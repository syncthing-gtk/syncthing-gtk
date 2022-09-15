"""
HTTP client classes
"""
import json
import logging
import os
import sys
import time
import urllib.parse

from gi.repository import Gio, GLib, GObject


log = logging.getLogger("HTTP")

# Random constant used as key when adding headers to returned data in
# REST requests; Anything goes, as long as it isn't string
HTTP_HEADERS = int(65513)


class RESTRequest(Gio.SocketClient):
    """
    REST over HTTP(s) request. Handles everything and calls callback with response
    received. It is assumed that response will always be JSON-encoded and
    it is automatically decoded.

    If request fails and error_callback is not set, it is automatically repeated.

    Callback signatures:
            callback(json_data, callback_data... )
            error_callback(exception, command, callback_data... )
    """

    def __init__(self, parent, command, callback, error_callback=None, *callback_data):
        Gio.SocketClient.__init__(self, tls=parent._tls)
        self._callback = callback
        self._error_callback = error_callback
        self._command = command
        self._parent = parent
        self._connection = None
        self._callback_data = callback_data or ()
        if parent._tls:
            GObject.Object.connect(self, "event", self._socket_event)

    def _connected(self, _self, results):
        """ Called after TCP connection is initiated """
        try:
            self._connection = self.connect_to_service_finish(results)
            if self._connection == None:
                raise Exception("Unknown error")
        except Exception as e:
            log.exception(e)
            if hasattr(e, "domain") and e.domain == "g-tls-error-quark":
                e = TLSUnsupportedException(e.message)
            self._error(e)
            return
        if self._epoch != self._parent._epoch:
            # Too late, throw it away
            self._connection.close(None)
            log.verbose("Discarded old connection for %s", self._command)
            return
        if self._parent._CSRFtoken is None and self._parent._api_key is None:
            # Request CSRF token first
            log.verbose("Requesting cookie")
            get_str = "\r\n".join([
                "GET / HTTP/1.0",
                "Host: %s" % self._parent._address,
                (("X-API-Key: %s" % self._parent._api_key)
                 if not self._parent._api_key is None else "X-nothing: x"),
                "Connection: close",
                "",
                "",
            ]).encode("utf-8")
        else:
            self._send_request()

    def _send_request(self):
        get_str = self._format_request()
        try:
            self._connection.get_output_stream().write_all(get_str, None)
        except Exception as e:
            self._error(e)
            return
        self._connection.get_input_stream().read_bytes_async(
            102400, 1, None, self._response)

    def _parse_csrf(self, response):
        for d in response:
            if d.startswith(b"Set-Cookie:"):
                for c in d.split(b":", 1)[1].split(b";"):
                    if c.strip().startswith(b"CSRF-Token-"):
                        self._CSRFtoken = c.strip(b" \r\n").decode()
                        log.verbose("Got new cookie: %s", self._CSRFtoken)
                        break
                if self._CSRFtoken != None:
                    break

    def _format_request(self):
        """
        Formats HTTP request (GET /xyz HTTP/1.0... ) before sending it to daemon
        """
        return "\r\n".join([
            "GET /rest/%s HTTP/1.0" % self._command,
            "Host: %s" % self._parent._address,
            "Cookie: %s" % self._parent._CSRFtoken,
            (("X-%s" % self._parent._CSRFtoken.replace("=", ": "))
             if self._parent._CSRFtoken else "X-nothing: x"),
            (("X-API-Key: %s" % self._parent._api_key)
             if not self._parent._api_key is None else "X-nothing2: x"),
            "Connection: close",
            "", ""
        ]).encode("utf-8")

    def _response(self, stream, results):
        try:
            response = stream.read_bytes_finish(results)
            if response == None:
                raise Exception("No data received")
        except Exception as e:
            self._connection.close(None)
            self._error(e)
            return
        if self._epoch != self._parent._epoch:
            # Too late, throw it away
            self._connection.close(None)
            log.verbose("Discarded old response for %s", self._command)
            return
        # Repeat read_bytes_async until entire response is read into buffer
        self._buffer.append(response.get_data())
        if response.get_size() > 0:
            self._connection.get_input_stream().read_bytes_async(
                102400, 1, None, self._response)
            return
        self._connection.close(None)
        response, self._buffer = (b"".join(self._buffer)), []
        if self._parent._CSRFtoken is None and self._parent._api_key is None:
            # I wanna cookie!
            self._parse_csrf(response.split(b"\n"))
            if self._parent._CSRFtoken == None:
                # This is pretty fatal and likely to fail again,
                # so request is not repeated automatically
                if self._error_callback == None:
                    log.error(
                        "Request '%s' failed: Error: failed to get CSRF cookie from daemon", self._command)
                else:
                    self._error(Exception("Failed to get CSRF cookie"))
                return
            # Repeat request with acquired cookie
            self.start()
            return
        # Split headers from response
        headers, response = self._split_headers(response)
        if headers is None:
            return
        # Parse response and call callback
        try:
            rdata = json.loads(response)
        except IndexError:  # No data
            rdata = {}
        except ValueError:  # Not a JSON
            rdata = {'data': response.decode('utf-8', errors='ignore')}
        if type(rdata) == dict:
            rdata[HTTP_HEADERS] = headers
        self._callback(rdata, *self._callback_data)

    def _split_headers(self, buffer):
        try:
            headers, response = buffer.split(b"\r\n\r\n", 1)
            headers = headers.decode('utf-8', errors='ignore').split("\r\n")
            code = int(headers[0].split(" ")[1])
            if code == 401:
                self._error(HTTPAuthException(buffer))
                return None, None
            elif code == 404:
                self._error(HTTPCode(404, "Not found", buffer, headers))
                return None, None
            elif code != 200:
                self._error(HTTPCode(code, response, buffer, headers))
                return None, None
        except Exception as e:
            # That probably wasn't HTTP
            import traceback
            traceback.print_exc()
            self._error(InvalidHTTPResponse(buffer))
            return None, None
        return headers, response

    def _error(self, exception):
        """ Error handler for _response method """
        if self._connection:
            self._connection.close(None)
            self._connection = None
        if self._error_callback:
            if self._epoch != self._parent._epoch:
                exception = ConnectionRestarted()
            self._error_callback(exception, self._command,
                                 *self._callback_data)
        elif self._epoch == self._parent._epoch:
            try:
                log.error("Request '%s' failed (%s); Repeating...",
                          self._command, exception)
            except UnicodeDecodeError:
                # Windows...
                log.error("Request '%s' failed; Repeating...", self._command)
            self._parent.timer(str(self), 1, self.start)

    def _socket_event(self, _self, event, connectable, con):
        """ Setups TSL certificate if HTTPS is used """
        if event == Gio.SocketClientEvent.TLS_HANDSHAKING:
            con.connect("accept-certificate", self._accept_certificate)

    def _accept_certificate(self, con, peer_cert, errors):
        """ Check if server presents expected certificate and accept connection """
        return peer_cert.is_same(self._parent._cert)

    def ignore_error(self):
        """
        Causes RESTRequest to ignore any error - no callback is called and
        request is *not* autorepeated.

        Returns self.
        """
        self._error_callback = lambda *a: True
        return self

    def start(self):
        if self._parent._address.startswith("127.0.0.1"):
            self.set_enable_proxy(False)
        self._epoch = self._parent._epoch
        self._buffer = []
        self.connect_to_host_async(
            self._parent._address, 0, None, self._connected)
        return self


class RESTPOSTRequest(RESTRequest):
    """ Similar to RESTRequest, but this one uses HTTP POST and sends data """

    def __init__(self, parent, command, data, callback, error_callback=None, *callback_data):
        RESTRequest.__init__(self, parent, command, callback,
                             error_callback, *callback_data)
        self._data = data

    def _format_request(self):
        """
        Formats POST request before sending it to daemon
        """
        try:
            data = dict(self._data)
            if HTTP_HEADERS in data:
                del data[HTTP_HEADERS]
            json_str = json.dumps(data)
        except TypeError:
            import yaml
            print(yaml.dump(data))
            raise
        return "\r\n".join([
            "POST /rest/%s HTTP/1.0" % self._command,
            "Host: %s" % self._parent._address,
            "Cookie: %s" % self._parent._CSRFtoken,
            (("X-%s" % self._parent._CSRFtoken.replace("=", ": "))
             if self._parent._CSRFtoken else "X-nothing: x"),
            (("X-API-Key: %s" % self._parent._api_key)
             if not self._parent._api_key is None else "X-nothing2: x"),
            "Content-Length: %s" % len(json_str),
            "Content-Type: application/json",
            "Connection: close",
            "",
            json_str
        ]).encode("utf-8")


class EventPollLoop(RESTRequest):
    """
    Event polling 'loop' continuously polls events from daemon using one HTTP(s)
    connection. If connection is broken, EventPollLoop reconnects automatically.
    'Loop' is canceled automatically when parent _epoch is increased.
    """

    def __init__(self, parent):
        RESTRequest.__init__(self, parent, "events", None, None)
        self._last_event_id = -1

    def _format_request(self):
        """
        Event request is as special as it gets, with HTTP/1.1, connection held
        and continuously requesting more and more data.
        """
        if self._last_event_id < 0:
            url = "/rest/events?limit=1"
        else:
            url = "/rest/events?since=%s" % (self._last_event_id,)

        return "\r\n".join([
            "GET %s HTTP/1.1" % url,
            "Host: %s" % self._parent._address,
            "Cookie: %s" % self._parent._CSRFtoken,
            (("X-%s" % self._parent._CSRFtoken.replace("=", ": "))
             if self._parent._CSRFtoken else "X-nothing: x"),
            (("X-API-Key: %s" % self._parent._api_key)
             if not self._parent._api_key is None else "X-nothing2: x"),
            "Cache-Control: no-cache",
            "Connection: keep-alive",
            "Pragma: no-cache",
            "", ""
        ]).encode("utf-8")

    def _error(self, exception):
        if self._connection:
            self._connection.close(None)
        if self._epoch == self._parent._epoch:
            if isinstance(exception, GLib.GError):
                # Connection terminated unexpectedly, Connection Refused
                if exception.code in (0, 39, 34):
                    self._parent._disconnected(message=str(exception))
                    return
            self._parent.timer(None, 1, self.start)

    def start(self):
        RESTRequest.start(self)
        self._buffer = b""

    def _response(self, stream, results):
        if self._parent._CSRFtoken is None and self._parent._api_key is None:
            return RESTRequest._response(self, stream, results)
        try:
            response = stream.read_bytes_finish(results)
            if response == None:
                raise Exception("No data received")
        except Exception as e:
            return self._error(e)
        if self._epoch != self._parent._epoch:
            self._connection.close(None)
            return

        buffer = response.get_data()
        assert type(buffer) == bytes
        headers, response = self._split_headers(buffer)
        if headers is None:
            return
        headers = {x: y.strip()
                   for (x, y) in [h.split(":", 1) for h in headers if ":" in h]}
        if "Transfer-Encoding" not in headers or headers["Transfer-Encoding"] != "chunked":
            # Something just went horribly wrong
            self._error(InvalidHTTPResponse(buffer))
            return
        self._buffer = response
        self._chunk_size = -1
        self._parse_chunk()

    def _chunk(self, stream, results):
        try:
            response = stream.read_bytes_finish(results)
            if response == None:
                raise Exception("nothing")
        except Exception as e:
            return self._error(e)
        if self._epoch != self._parent._epoch:
            self._connection.close(None)
            return
        data = response.get_data()
        if len(data) == 0:
            # Connection broken
            self._connection.close(None)
            return self.start()
        self._buffer += data
        self._parse_chunk()

    def _resend_request(self):
        """ Sends another request using same connection """
        self._chunk_size = -1
        get_str = "\r\n".join([
            "GET /rest/events?since=%s HTTP/1.1" % (self._last_event_id,),
            "Host: %s" % self._parent._address,
            (("X-API-Key: %s" % self._parent._api_key)
             if not self._parent._api_key is None else "X-nothing: x"),
            "",
            "",
        ]).encode("utf-8")
        try:
            self._connection.get_output_stream().write_all(get_str, None)
        except Exception as e:
            self._connection.close(None)
            return self.start()
        self._connection.get_input_stream().read_bytes_async(10, 1, None, self._chunk)

    def _parse_chunk(self):
        if self._chunk_size < 0:
            try:
                # Try to decode chunk. May raise exception if only very few bytes
                # have been read so far
                size_str, rest = self._buffer.split(b"\r\n", 1)
                self._chunk_size = int(size_str, 16)
                self._buffer = rest
                if self._chunk_size < 1:
                    # Zero-sized chunk means end of transfer
                    return self._resend_request()
                self._chunk_size += 2  # 2b for following \r\n
            except (ValueError, IndexError):
                self._chunk_size = -1
                self._connection.get_input_stream().read_bytes_async(100, 1, None, self._chunk)
                return
        retrieved = len(self._buffer)
        if retrieved < self._chunk_size:
            self._connection.get_input_stream().read_bytes_async(
                self._chunk_size - retrieved, 1, None, self._chunk)
            return

        response, self._buffer = self._buffer[0:
                                              retrieved], self._buffer[retrieved:]
        try:
            events = json.loads(response)
        except Exception:
            # Invalid response
            self._connection.close(None)
            return self.start()

        for event in events:
            if self._last_event_id >= 0 and event["id"] != self._last_event_id + 1:
                # Event IDs are not continuous, something just went horribly wrong
                # There is only one case when this is expected: When connection
                # to daemon is lost and ST-GTK unknowingly reconnects to
                # different instance.
                return self._parent._instance_replaced()
            self._last_event_id = event["id"]
            self._parent._on_event(event)
            sys.stdout.flush()

        self._resend_request()


class InvalidConfigurationException(RuntimeError):
    pass


class TLSUnsupportedException(RuntimeError):
    pass


class TLSErrorException(RuntimeError):
    pass


class HTTPError(RuntimeError):
    def __init__(self, message, full_response):
        RuntimeError.__init__(self, message)
        self.full_response = full_response


class InvalidHTTPResponse(HTTPError):
    def __init__(self, full_response):
        HTTPError.__init__(self, "Invalid HTTP response", full_response)


class HTTPCode(HTTPError):
    def __init__(self, code, message, full_response, headers=[]):
        HTTPError.__init__(self, "HTTP error %s : %s" %
                           (code, message), full_response)
        self.code = code
        self.message = message
        self.headers = headers

    def __str__(self):
        if self.message is None:
            return "HTTP/%s" % (self.code,)
        else:
            return "HTTP/%s: %s" % (self.code, self.message)


class HTTPAuthException(HTTPCode):
    def __init__(self, full_response):
        HTTPCode.__init__(self, 401, None, full_response)

    def __str__(self):
        return "HTTP/401 Unauthorized"


class ConnectionRestarted(Exception):
    def __init__(self):
        Exception.__init__(self, "Connection was restarted after request")
