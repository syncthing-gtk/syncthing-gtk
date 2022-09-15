#!/usr/bin/env python3
"""
Syncthing-GTK - Daemon

Class interfacing with syncthing daemon

Create instance, connect singal handlers and call daemon.reconnect()

"""


import json
import logging
import os
import sys
import time
import urllib.parse
from datetime import datetime
from xml.dom import minidom

from dateutil import tz
from gi.repository import Gio, GLib, GObject

from syncthing_gtk.http import (
    HTTP_HEADERS,
    ConnectionRestarted,
    EventPollLoop,
    HTTPAuthException,
    HTTPCode,
    HTTPError,
    InvalidConfigurationException,
    InvalidHTTPResponse,
    RESTPOSTRequest,
    RESTRequest,
    TLSErrorException,
    TLSUnsupportedException,
)
from syncthing_gtk.timermanager import TimerManager
from syncthing_gtk.tools import compare_version, get_config_dir, get_header, parsetime


log = logging.getLogger("Daemon")

# Minimal version supported by Daemon class
MIN_VERSION = "0.14"

# Last-seen values before this date are translated to never
NEVER = datetime(1971, 1, 1, 1, 1, 1, tzinfo=tz.tzlocal())


class Daemon(GObject.GObject, TimerManager):
    """
    Object for interacting with syncthing daemon.

    List of signals:
            config-out-of-sync ()
                    Emitted when daemon synchronization gets out of sync and
                    daemon needs to be restarted.

            config-saved ()
                    Emitted when daemon saves configuration without need for
                    restarting.

            connected ()
                    Emitted when connection to daemon is initiated, before
                    configuration is loaded and parsed.

            disconnected (reason, message)
                    Emitted after connection to daemon is lost. Connection can
                    be reinitiated by calling reconnect()
                            reason :	Daemon.SHUTDOWN if connection is closed
                                                    after calling shutdown()
                                                    Daemon.RESTART if connection is closed
                                                    after calling restart()
                                                    Daemon.UNEXPECTED for all other cases
                            message:	generated error message

            config-loaded(config)
                    Emitted while connection do daemon is being created, when
                    configuration is loaded from daemon.
                            config:		decoded /rest/config YAML file

            connection-error (reason, message, exception)
                    Emitted if connection to daemon fails.
                            reason:		Daemon.REFUSED if connection is refused and
                                                    daemon probably offline. Connection will be
                                                    retried automatically.
                                                    Daemon.UNKNOWN for all other problems.
                                                    Connection can be reinitiated by calling
                                                    reconnect() in this case.
                            message:	generated error message
                            exception:	Exeception that caused problem or None

            my-id-changed (my_id, replaced)
                    Emitted when ID is retrieved from device or when ID changes
                    after client connects to another device
                            my_id:		ID of device that is instance connected to.

            error (message)
                    Emitted every time when daemon generates error readable by
                    WebUI (/rest/errors call)
                            message:	Error message sent by daemon

            folder-rejected(device_id, folder_id, label)
                    Emitted when daemon detects unexpected folder from known
                    device.
                            device_id:	id of device that send unexpected folder id
                            folder_id:	id of unexpected folder
                            label:		label of unexpected folder or None

            device-rejected(device_id, device_name, address)
                    Emitted when daemon detects connection from unknown device
                            device_id:		device id
                            device_name:	device name
                            address:		address which connection come from

            device-added (id, name, used, data)
                    Emited when new device is loaded from configuration
                            id:		id of loaded device
                            name:	name of loaded device (may be None)
                            used:	true if there is any folder shared with this device
                            data:	dict with rest of device data

            device-connected (id)
                    Emitted when daemon connects to remote device
                            id:			id of device

            device-disconnected (id)
                    Emitted when daemon loses connection to remote device
                            id:			id of device

            device-discovered (id, addresses)
                    # TODO: What this event does?
                            id:			id of device
                            addresses:	list of device addresses

            device-data-changed (id, address, version, inbps, outbps, inbytes, outbytes)
                    Emitted when device data changes
                            id:			id of device
                            address:	address of remote device
                            version:	daemon version of remote device
                            inbps:		download rate
                            outbps:	upload rate
                            inbytes:	total number of bytes downloaded
                            outbytes:	total number of bytes uploaded

            last-seen-changed (id, last_seen)
                    Emitted when daemon reported 'last seen' value for device changes
                    or when is this value received for first time
                            id:			id of device
                            last_seen:	datetime object or None, if device was never seen

            device-paused (id):
                    Emitted when synchronization with device is paused
                            id:		id of folder

            device-resumed (id):
                    Emitted when synchronization with device is resumed
                            id:		id of folder

            device-sync-started (id, progress):
                    Emitted after device synchronization is started
                            id:			id of folder
                            progress:	synchronization progress (0.0 to 1.0)

            device-sync-progress (id, progress):
                    Emitted repeatedly while device is being synchronized
                            id:			id of folder
                            progress:	synchronization progress (0.0 to 1.0)

            device-sync-finished (id):
                    Emitted after device synchronization is finished
                            id:		id of folder

            folder-added (id, data)
                    Emitted when new folder is loaded from configuration
                            id:		id of loaded folder
                            data:	dict with rest of folder data

            folder-error (id, errors)
                    Emitted when when a folder cannot be successfully synchronized
                            id:		id of loaded folder
                            errors:	list with errors

            folder-data-changed (id, data):
                    Emitted when change in folder data (/rest/model call)
                    is detected and successfully loaded.
                            id:		id of folder
                            data:	dict with loaded data

            folder-data-failed (id):
                    Emitted when daemon fails to load folder data (/rest/model call),
                    most likely because folder was just added and syncthing
                    daemon needs to be restarted
                            id:		id of folder

            folder-scan-progress (id, progress):
                    Emitted repeatedly while folder is being scanned
                            id:			id of folder
                            progress:	scan progress (0.0 to 1.0)

            folder-sync-progress (id, progress):
                    Emitted repeatedly while folder is being synchronized
                            id:			id of folder
                            progress:	synchronization progress (0.0 to 1.0)

            folder-sync-finished (id):
                    Emitted after folder synchronization is finished
                            id:		id of folder

            folder-scan-started (id):
                    Emitted after folder scan is started
                            id:		id of folder

            folder-scan-finished (id):
                    Emitted after folder scan is finished
                            id:		id of folder

            folder-stopped (id, message):
                    Emitted when folder enters 'stopped' state.
                    No 'folder-sync', 'folder-sync-progress' and 'folder-scan-started'
                    events are emitted after folder enters this state, until
                    reconnect() is called.
                            id:			id of folder
                            message:	error message

            item-started (folder_id, filename, time):
                    Emitted when synchronization of file starts
                            folder_id:	id of folder that contains file
                            filename:	synchronized file
                            time:		event timestamp

            item-updated (folder_id, filename, time):
                    Emited when change in local file is detected (LocalIndexUpdated event)
                            folder_id:	id of folder that contains file
                            filename:	updated file
                            time:		event timestamp

            startup-complete():
                    Emited when daemon initialization is complete.

            system-data-updated (ram_ussage, cpu_ussage, d_failed, d_total)
                    Emitted every time when system information is received
                    from daemon.
                            ram_ussage:	memory ussage in bytes
                            cpu_ussage:	CPU ussage in percent (0.0 to 100.0)
                            d_failed:	Number of discovery servers that daemon failed to
                                                    connect to
                            d_total:	Total number of discovery servers
    """

    __gsignals__ = {
        "config-out-of-sync": (GObject.SIGNAL_RUN_FIRST, None, ()),
        "config-saved": (GObject.SIGNAL_RUN_FIRST, None, ()),
        "connected": (GObject.SIGNAL_RUN_FIRST, None, ()),
        "disconnected": (GObject.SIGNAL_RUN_FIRST, None, (int, object)),
        "config-loaded": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "connection-error": (GObject.SIGNAL_RUN_FIRST, None, (int, object, object)),
        "error": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "folder-rejected": (GObject.SIGNAL_RUN_FIRST, None, (object, object, object)),
        "device-rejected": (GObject.SIGNAL_RUN_FIRST, None, (object, object, object)),
        "my-id-changed": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "device-added": (GObject.SIGNAL_RUN_FIRST, None, (object, object, bool, object)),
        "device-connected": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "device-disconnected": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "device-discovered": (GObject.SIGNAL_RUN_FIRST, None, (object, object,)),
        "device-data-changed": (GObject.SIGNAL_RUN_FIRST, None, (object, object, object, float, float, object, object)),
        "last-seen-changed": (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        "device-paused": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "device-resumed": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "device-sync-started": (GObject.SIGNAL_RUN_FIRST, None, (object, float)),
        "device-sync-progress": (GObject.SIGNAL_RUN_FIRST, None, (object, float)),
        "device-sync-finished": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "folder-added": (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        "folder-error": (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        "folder-data-changed": (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        "folder-data-failed": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "folder-sync-finished": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "folder-sync-progress": (GObject.SIGNAL_RUN_FIRST, None, (object, float)),
        "folder-sync-started": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "folder-scan-finished": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "folder-scan-started": (GObject.SIGNAL_RUN_FIRST, None, (object,)),
        "folder-scan-progress": (GObject.SIGNAL_RUN_FIRST, None, (object, float)),
        "folder-stopped": (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        "item-started": (GObject.SIGNAL_RUN_FIRST, None, (object, object, object)),
        "item-updated": (GObject.SIGNAL_RUN_FIRST, None, (object, object, object)),
        "startup-complete": (GObject.SIGNAL_RUN_FIRST, None, ()),
        "system-data-updated": (GObject.SIGNAL_RUN_FIRST, None, (int, float, int, int)),
    }

    # Constants for 'reason' parameter of disconnected event
    UNEXPECTED = 0  # connection closed by daemon
    SHUTDOWN = 1
    RESTART = 2

    # Constants for 'reason' parameter of connection-error event
    REFUSED = 1
    NOT_AUTHORIZED = 2
    OLD_VERSION = 3
    TLS_UNSUPPORTED = 4
    UNKNOWN = 255

    def __init__(self, syncthing_configxml=None):
        GObject.GObject.__init__(self)
        TimerManager.__init__(self)
        self._CSRFtoken = None
        self._address = None
        self._api_key = None
        self._connected = False
        self._refresh_interval = 1  # seconds
        self._configxml = syncthing_configxml
        # syncing_folders holds set of folders that are being synchronized
        self._syncing_folders = set()
        # stopped_folders holds set of folders in 'stopped' state
        # No 'folder-sync', 'folder-sync-progress' and 'folder-scan-started'
        # events are emitted after folder enters this state
        self._stopped_folders = set()
        # syncing_devices does same thing, only for devices
        self._syncing_devices = set()
        # and once again, for folders in 'Scanning' state
        self._scanning_folders = set()
        # device_data stores data needed to compute transfer speeds
        # and synchronization state
        self._device_data = {}
        # folder_devices stores list of devices assigned to folder
        self._folder_devices = {}
        # last_seen holds last_seen value for each folder, preventing firing
        # last-seen-changed event with same values twice
        self._last_seen = {}
        # last_error_time is used to discard repeating errors
        self._last_error_time = None  # Time is taken for first event
        # last_id is id of last event received from daemon
        self._last_id = 0
        # Epoch is increased when reconnect() method is called; It is
        # used to discard responses for old REST requests
        self._epoch = 1
        self._instance_id = None
        self._my_id = None
        self._read_config()

    ### Internal stuff ###

    def _read_config(self):
        # Read syncthing config to get connection url
        if not self._configxml:
            self._configxml = os.path.join(
                get_config_dir(), "syncthing", "config.xml")
        if not os.path.exists(self._configxml) and os.path.exists(os.path.expanduser("~/snap/syncthing/common/syncthing")):
            # Special case for syncthing in snap package
            self._configxml = os.path.expanduser(
                "~/snap/syncthing/common/syncthing/config.xml")
        try:
            log.debug("Reading syncthing config %s", self._configxml)
            with open(self._configxml, "r") as f:
                config = f.read()
        except Exception as e:
            raise InvalidConfigurationException(
                "Failed to read daemon configuration: %s" % e)
        try:
            xml = minidom.parseString(config)
        except Exception as e:
            raise InvalidConfigurationException(
                "Failed to parse daemon configuration: %s" % e)
        tls = "false"
        try:
            tls = xml.getElementsByTagName("configuration")[0] \
                .getElementsByTagName("gui")[0].getAttribute("tls")
        except Exception as e:
            pass
        self._tls = False
        self._cert = None
        if tls.lower() == "true":
            self._tls = True
            try:
                self._cert = Gio.TlsCertificate.new_from_file(
                    os.path.join(get_config_dir(), "syncthing", "https-cert.pem"))
            except Exception as e:
                log.exception(e)
                raise TLSErrorException("Failed to load daemon certificate")
        try:
            self._address = xml.getElementsByTagName("configuration")[0] \
                .getElementsByTagName("gui")[0] \
                .getElementsByTagName("address")[0] \
                .firstChild.nodeValue
            if self._address.startswith("0.0.0.0"):
                addr, port = self._address.split(":", 1)
                self._address = "127.0.0.1:%s" % (port,)
                log.debug(
                    "WebUI listens on 0.0.0.0, connecting to 127.0.0.1 instead")
        except Exception as e:
            log.exception(e)
            raise InvalidConfigurationException(
                "Required configuration node not found in daemon config file")
        try:
            self._api_key = xml.getElementsByTagName("configuration")[0] \
                .getElementsByTagName("gui")[0] \
                .getElementsByTagName("apikey")[0] \
                .firstChild.nodeValue
        except Exception as e:
            # API key can be none
            pass

    def override_config(self, address, api_key):
        """
        Can be used to override settings loaded from config file.
        api_key can be None.
        """
        self._address = address
        self.api_key = api_key

    def _get_device_data(self, nid):
        """ Returns dict with device data, creating it if needed """
        if not nid in self._device_data:
            self._device_data[nid] = {
                "inBytesTotal": 0, "outBytesTotal": 0,
                "inbps": 0, "outbps": 0, "clientVersion": "?",
                            "address": "", "completion": {}, "connected": False,
            }
        return self._device_data[nid]

    def _request_config(self, *a):
        """ Request settings from syncthing daemon """
        RESTRequest(self, "system/config", self._syncthing_cb_config,
                    self._syncthing_cb_config_error).start()

    def _request_folder_data(self, folder_id):
        id_enc = urllib.parse.quote(folder_id.encode('utf-8'))
        RESTRequest(self, "db/status?folder=%s" % (id_enc,), self._syncthing_cb_folder_data,
                    self._syncthing_cb_folder_data_failed, folder_id).start()

    def _request_last_seen(self, *a):
        """ Request 'last seen' values for all devices """
        RESTRequest(self, "stats/device",
                    self._syncthing_cb_last_seen).ignore_error().start()

    def _parse_dev_n_folders(self, config):
        """
        Parses devices and folders from configuration and emits
        associated events.
        """
        # Pre-parse folders to detect unused devices
        device_folders = {}
        for r in config["folders"]:
            rid = r["id"]
            for n in r["devices"]:
                nid = n["deviceID"]
                if not nid in device_folders:
                    device_folders[nid] = []
                device_folders[nid].append(rid)

        # Parse devices
        for n in sorted(config["devices"], key=lambda x: x["name"].lower()):
            nid = n["deviceID"]
            self._get_device_data(nid)  # Creates dict with device data
            used = (nid in device_folders) and (len(device_folders[nid]) > 0)
            self.emit("device-added", nid, n["name"], used, n)

        # Parse folders
        for r in sorted(config["folders"], key=lambda x: x["id"].lower()):
            rid = r["id"]
            self._syncing_folders.add(rid)
            self._folder_devices[rid] = [n["deviceID"] for n in r["devices"]]
            self.emit("folder-added", rid, r)
            self._request_folder_data(rid)

    ### Callbacks ###

    def _syncthing_cb_shutdown(self, data, reason):
        """ Callback for 'shutdown' AND 'restart' request """
        if 'ok' in data:
            if self._connected:
                self._connected = False
                self._epoch += 1
                self.emit("disconnected", reason, "")
            self.cancel_all()

    def _syncthing_cb_errors(self, errors):
        if errors["errors"] is not None:
            for e in errors["errors"]:
                if "time" in e:
                    # TODO: Remove this next time support for older daemon is dropped
                    t = parsetime(e["time"])
                    msg = e["error"]
                elif "when" in e:
                    t = parsetime(e["when"])
                    msg = e["message"]
                else:
                    # Can't decode this
                    continue
                if t > self._last_error_time:
                    self.emit("error", msg)
                    self._last_error_time = t
        r = RESTRequest(self, "system/error", self._syncthing_cb_errors)
        self.timer("errors", self._refresh_interval * 5, r.start)

    def _syncthing_cb_connections(self, data, prev_time):
        now = time.time()
        td = now - prev_time

        cons = data["connections"]
        # Use my own device for totals, if it is already known
        # It it is not known, just skip totals for now
        if not self._my_id is None:
            cons[self._my_id].update(data["total"])

        for id in cons:
            # Load device data
            nid = id
            device_data = self._get_device_data(nid)

            # Compute rates
            try:
                cons[id]["inbps"] = max(
                    0.0, (cons[id]["inBytesTotal"] - device_data["inBytesTotal"]) / td)
                cons[id]["outbps"] = max(
                    0.0, (cons[id]["outBytesTotal"] - device_data["outBytesTotal"]) / td)
            except Exception:
                cons[id]["inbps"] = 0.0
                cons[id]["outbps"] = 0.0
            # Store updated device_data
            for key in cons[id]:
                if not key in ('clientVersion', 'connected'):		# Don't want copy those
                    if cons[id][key] != "":							# Happens for 'total'
                        device_data[key] = cons[id][key]

            if "clientVersion" in cons[id] and cons[id]["clientVersion"] != "":
                device_data["clientVersion"] = cons[id]["clientVersion"]

            if cons[id]["paused"]:
                # Send "device-paused" signal if device needed
                device_data["connected"] = False
                self.emit("device-paused", nid)
            else:
                # Send "device-connected" signal, if device was disconnected until now
                if cons[id]["connected"]:
                    if not device_data["connected"] and nid != self._my_id:
                        device_data["connected"] = True
                        self.emit("device-connected", nid)
            # Send "device-data-changed" signal
            self.emit("device-data-changed", nid,
                      device_data["address"],
                      device_data["clientVersion"],
                      device_data["inbps"],
                      device_data["outbps"],
                      device_data["inBytesTotal"],
                      device_data["outBytesTotal"])

        # ... repeat until pronounced dead
        r = RESTRequest(self, "system/connections",
                        self._syncthing_cb_connections, None, now)
        self.timer("conns", self._refresh_interval * 5, r.start)

    def _syncthing_cb_last_seen(self, data):
        for nid in data:
            if nid != HTTP_HEADERS:
                t = parsetime(data[nid]["lastSeen"])
                if t < NEVER:
                    t = None
                if not nid in self._last_seen or self._last_seen[nid] != t:
                    self._last_seen[nid] = t
                    self.emit('last-seen-changed', nid, t)

    def _syncthing_cb_completion(self, data):
        nid = data["device"]
        rid = data["folder"]
        # Store acquired value
        device = self._get_device_data(nid)
        device["completion"][rid] = float(data["completion"])

        # Recompute stuff
        total = 100.0 * len(device["completion"])
        sync = 0.0
        if total > 0.0:
            sync = sum(device["completion"].values()) / total
        if sync <= 0 or sync >= 100:
            # Not syncing
            if nid in self._syncing_devices:
                self._syncing_devices.discard(nid)
                self.emit("device-sync-finished", nid)
        else:
            # Syncing
            if not nid in self._syncing_devices:
                self._syncing_devices.add(nid)
                self.emit("device-sync-started", nid, sync)
            else:
                self.emit("device-sync-progress", nid, sync)

    def _syncthing_cb_system(self, data):
        if "myID" not in data:
            # Invalid response
            r = RESTRequest(self, "system/status", self._syncthing_cb_system)
            log.warning(
                "Invalid response received for rest/system/status request")
            self.timer("system", self._refresh_interval * 5, r.start)
            return

        if self._my_id != data["myID"]:
            if self._my_id != None:
                # Can myID be ever changed?
                log.warning("My ID has been changed on the fly")
            self._my_id = data["myID"]
            self.emit('my-id-changed', self._my_id)
            version = get_header(data[HTTP_HEADERS], "X-Syncthing-Version")
            if version:
                self._syncthing_cb_version_known(version)
            else:
                RESTRequest(self, "system/version",
                            self._syncthing_cb_version).start()

        d_failed, d_total = 0, 0
        if "discoveryEnabled" in data and data["discoveryEnabled"]:
            d_total = data["discoveryMethods"]
            d_failed = len(data["discoveryErrors"])

        if "startTime" in data:
            if self._instance_id is None:
                self._instance_id = data["startTime"]
            else:
                if self._instance_id != data["startTime"]:
                    return self._instance_replaced()

        self.emit('system-data-updated', data["sys"],
                  float(data["cpuPercent"]), d_failed, d_total)

        r = RESTRequest(self, "system/status", self._syncthing_cb_system)
        self.timer("system", self._refresh_interval * 5, r.start)

    def _instance_replaced(self):
        """
        Called when it is detected that syncthing daemon instance is no longer
        same as we talked to before
        """
        log.warning(
            "Daemon instance was replaced unexpectedly. Disconnecting from daemon.")
        self._disconnected(message="Daemon instance replaced unexpectedly")

    def _disconnected(self, reason=UNEXPECTED, message=""):
        """ Called to prepare and emit "disconnected" signal """
        self._my_id = None
        if self._connected:
            self._connected = False
            self._epoch += 1
            self.emit("disconnected", reason, message)
        self.cancel_all()

    def _syncthing_cb_version(self, data):
        if "version" in data:
            # New since https://github.com/syncthing/syncthing/commit/d7956dd4957fa6eee5971c072fd7181015fa876c
            version = data["version"]
        else:
            version = data["data"]
        self._syncthing_cb_version_known(version)

    def _syncthing_cb_version_known(self, version):
        """
        Called when version is received from daemon, either by
        calling /rest/version or from X-Syncthing-Version header.
        """
        if not compare_version(version, MIN_VERSION):
            # Syncting version too low. Cancel everything and report error
            self.cancel_all()
            self._epoch += 1
            msg = "daemon is too old"
            self.emit("connection-error", Daemon.OLD_VERSION,
                      msg, Exception(msg))
            return
        if self._my_id != None:
            device = self._get_device_data(self._my_id)
            if version != device["clientVersion"]:
                device["clientVersion"] = version
                self.emit("device-data-changed", self._my_id,
                          None,
                          device["clientVersion"],
                          device["inbps"], device["outbps"],
                          device["inBytesTotal"], device["outBytesTotal"])

    def _syncthing_cb_folder_data(self, data, rid):
        state = data['state']
        if state in ('error', 'stopped'):
            if not rid in self._stopped_folders:
                self._stopped_folders.add(rid)
                reason = data["invalid"] or data["error"]
                self.emit("folder-stopped", rid, reason)
        self.emit('folder-data-changed', rid, data)
        p = 0.0
        if state == "syncing":
            if float(data["globalBytes"]) > 0.0:
                p = float(data["inSyncBytes"]) / float(data["globalBytes"])
        self._folder_state_changed(rid, state, p)

    def _syncthing_cb_folder_data_failed(self, exception, request, rid):
        self.emit('folder-data-failed', rid)

    def _syncthing_cb_config(self, config):
        """
        Called when configuration is loaded from syncthing daemon.
        After configuration is successfully parsed, app starts querying for events
        """
        if not self._connected:
            self._connected = True
            self.emit('connected')

            self._parse_dev_n_folders(config)

            EventPollLoop(self).start()
            RESTRequest(self, "system/config/insync",
                        self._syncthing_cb_config_in_sync).start()
            RESTRequest(self, "system/connections",
                        self._syncthing_cb_connections, None, time.time()).start()
            RESTRequest(self, "system/status",
                        self._syncthing_cb_system).start()
            self._request_last_seen()
            self.check_config()
            self.emit('config-loaded', config)

    def _syncthing_cb_config_error(self, exception, command):
        self.cancel_all()
        if isinstance(exception, GLib.GError):
            # Connection Refused / Cannot connect to destination
            if exception.code in (0, 39, 34, 45):
                # It usually means that daemon is not yet fully started or not running at all.
                epoch = self._epoch
                self.emit("connection-error", Daemon.REFUSED,
                          exception.message, exception)
                if epoch == self._epoch:
                    r = RESTRequest(
                        self, "system/config", self._syncthing_cb_config, self._syncthing_cb_config_error)
                    self.timer("config", self._refresh_interval, r.start)
                return
        elif isinstance(exception, HTTPAuthException):
            self.emit("connection-error", Daemon.NOT_AUTHORIZED,
                      exception.message, exception)
            return
        elif isinstance(exception, HTTPCode):
            # HTTP 404 may actually mean old daemon version
            version = get_header(exception.headers, "X-Syncthing-Version")
            if version != None and not compare_version(version, MIN_VERSION):
                self._epoch += 1
                msg = "daemon is too old"
                self.emit("connection-error", Daemon.OLD_VERSION,
                          msg, Exception(msg))
            else:
                self.emit("connection-error", Daemon.UNKNOWN,
                          exception.message, exception)
            return
        elif isinstance(exception, TLSUnsupportedException):
            self.emit("connection-error", Daemon.TLS_UNSUPPORTED,
                      exception.message, exception)
            return
        elif isinstance(exception, ConnectionRestarted):
            # Happens on Windows. Just try again.
            GLib.idle_add(self._request_config)
            return
        elif isinstance(exception, TLSUnsupportedException):
            self.emit("connection-error", Daemon.TLS_UNSUPPORTED,
                      exception.message, exception)
            return
        self.emit("connection-error", Daemon.UNKNOWN,
                  exception.message, exception)

    def _syncthing_cb_config_in_sync(self, data):
        """
        Handler for config/sync response. Emits 'config-out-of-sync' if
        configuration is not in sync.
        """
        if "configInSync" in data:
            if not data["configInSync"]:
                # Not in sync...
                self.emit("config-out-of-sync")

    def _folder_state_changed(self, rid, state, progress):
        """
        Emits event according to last known and new state.
        """
        if state != "syncing" and rid in self._syncing_folders:
            self._syncing_folders.discard(rid)
            if not rid in self._stopped_folders:
                self.emit("folder-sync-finished", rid)
        if state != "scanning" and rid in self._scanning_folders:
            self._scanning_folders.discard(rid)
            if not rid in self._stopped_folders:
                self.emit("folder-scan-finished", rid)
        if state == "syncing":
            if not rid in self._stopped_folders:
                if rid in self._syncing_folders:
                    self.emit("folder-sync-progress", rid, progress)
                else:
                    self._syncing_folders.add(rid)
                    self.emit("folder-sync-started", rid)
        elif state == "scanning":
            if not rid in self._stopped_folders:
                if not rid in self._scanning_folders:
                    self._scanning_folders.add(rid)
                    self.emit("folder-scan-started", rid)

    def _on_event(self, e):
        eType = e["type"]
        if eType in ("Ping", "Starting"):
            # Just ignore ignore those
            pass
        elif eType == "StartupComplete":
            self.emit("startup-complete")
        elif eType == "StateChanged":
            state = e["data"]["to"]
            rid = e["data"]["folder"]
            self._folder_state_changed(rid, state, 0)
        elif eType in ("RemoteIndexUpdated"):
            pass
        elif eType == "DeviceConnected":
            nid = e["data"]["id"]
            self.emit("device-connected", nid)
        elif eType == "DeviceDisconnected":
            nid = e["data"]["id"]
            self.emit("device-disconnected", nid)
        elif eType == "DeviceDiscovered":
            nid = e["data"]["device"]
            addresses = e["data"]["addrs"]
            self.emit("device-discovered", nid, addresses)
        elif eType == "DevicePaused":
            nid = e["data"]["device"]
            self.emit("device-paused", nid)
        elif eType == "DeviceResumed":
            nid = e["data"]["device"]
            self.emit("device-resumed", nid)
            self._request_last_seen()
        elif eType == "FolderRejected":
            nid = e["data"]["device"]
            rid = e["data"]["folder"]
            label = e["data"]["folderLabel"] if "folderLabel" in e["data"] else None
            self.emit("folder-rejected", nid, rid, label)
        elif eType == "DeviceRejected":
            nid = e["data"]["device"]
            name = e["data"]["name"]
            address = e["data"]["address"]
            self.emit("device-rejected", nid, name, address)
        elif eType == "FolderScanProgress":
            rid = e["data"]["folder"]
            total = float(e["data"]["total"])
            if total > 0:
                # ^^ just in case
                status = float(e["data"]["current"]) / total
                self.emit("folder-scan-progress", rid, status)
        elif eType == "ItemStarted":
            rid = e["data"]["folder"]
            filename = e["data"]["item"]
            t = parsetime(e["time"])
            self.emit("item-started", rid, filename, t)
        elif eType == "FolderCompletion":
            self._syncthing_cb_completion(e["data"])
        elif eType == "FolderSummary":
            rid = e["data"]["folder"]
            self._syncthing_cb_folder_data(e["data"]["summary"], rid)
        elif eType == "FolderErrors":
            rid = e["data"]["folder"]
            self.emit("folder-error", rid, e["data"]["errors"])
        elif eType == "ConfigSaved":
            self.emit("config-saved")
        elif eType == "ItemFinished":
            rid = e["data"]["folder"]
            if e["data"]["error"] is None:
                filename = e["data"]["item"]
                t = parsetime(e["time"])
                self.emit("item-updated", rid, filename, t)
        elif eType in ("ItemFinished", "DownloadProgress", "RelayStateChanged", "LocalIndexUpdated", "ListenAddressesChanged", "LoginAttempt"):
            # Not handled
            pass
        else:
            log.warning("Unhandled event type: %s", e)

    ### External stuff ###

    def reconnect(self):
        """
        Cancel all pending requests, throw away all data and (re)connect.
        Should be called from glib loop
        """
        self.close()
        GLib.idle_add(self._request_config)

    def reload_config(self, callback=None, error_callback=None):
        """
        Reloads config from syncthing daemon.
        Calling this will cause or may cause emiting following events
        with reloaded data:
        - folder-added
        - device-added
        - config-out-of-sync
        """
        def reload_config_cb(config):
            self._parse_dev_n_folders(config)
            if not callback is None:
                callback()
            RESTRequest(self, "system/config/insync",
                        self._syncthing_cb_config_in_sync).start()
        RESTRequest(self, "system/config", reload_config_cb,
                    error_callback).start()

    def close(self):
        """
        Terminates everything, cancel all pending requests, throws away
        data.
        Works like reconnect(), but without reconnecting.
        """
        self._my_id = None
        self._instance_id = None
        self._connected = False
        self._syncing_folders = set()
        self._stopped_folders = set()
        self._syncing_devices = set()
        self._scanning_folders = set()
        self._device_data = {}
        self._folder_devices = {}
        self._last_id = 0
        self._last_seen = {}
        self.cancel_all()
        self._epoch += 1

    def check_config(self):
        """
        Check if configuration is in sync.
        Should cause 'config-out-of-sync' event to be raised ASAP.
        """
        RESTRequest(self, "system/config/insync",
                    self._syncthing_cb_config_in_sync).start()

    def read_config(self, callback, error_callback=None, *calbackdata):
        """
        Asynchronously reads last configuration version from daemon
        (even if this version is not currently used). Calls
        callback(config) with data decoded from json on success,
        error_callback(exception) on failure
        """
        RESTRequest(self, "system/config", callback,
                    error_callback, *calbackdata).start()

    def write_config(self, config, callback, error_callback=None, *calbackdata):
        """
        Asynchronously POSTs new configuration to daemon. Calls
        callback() on success, error_callback(exception) on failure.
        Should cause 'config-out-of-sync' event to be raised ASAP.
        """
        def run_before(data, *a):
            self.check_config()
            callback(*calbackdata)
        RESTPOSTRequest(self, "system/config", config, run_before,
                        error_callback, *calbackdata).start()

    def read_stignore(self, folder_id, callback, error_callback=None, *calbackdata):
        """
        Asynchronously reads .stignore data from from daemon.
        Calls callback(text) with .stignore content on success,
        error_callback(exception) on failure
        """
        def r_filter(data, *a):
            if "ignore" in data and not data["ignore"] is None:
                callback("\n".join(data["ignore"]).strip(" \t\n"), *a)
            else:
                callback("", *a)
        id_enc = urllib.parse.quote(folder_id.encode('utf-8'))
        RESTRequest(self, "db/ignores?folder=%s" % (id_enc,),
                    r_filter, error_callback, *calbackdata).start()

    def write_stignore(self, folder_id, text, callback, error_callback=None, *calbackdata):
        """
        Asynchronously POSTs .stignore to daemon. Calls callback()
        with on success, error_callback(exception) on failure.
        """
        data = {'ignore': text.split("\n")}
        id_enc = urllib.parse.quote(folder_id.encode('utf-8'))
        RESTPOSTRequest(self, "db/ignores?folder=%s" % (id_enc,),
                        data, callback, error_callback, *calbackdata).start()

    def restart(self):
        """
        Asks daemon to restart. If successful, call will cause
        'disconnected' event with Daemon.RESTART reason to be fired
        """
        RESTPOSTRequest(self, "system/restart",  {},
                        self._syncthing_cb_shutdown, None, Daemon.RESTART).start()

    def shutdown(self):
        """
        Asks daemon to shutdown. If successful, call will cause
        'disconnected' event with Daemon.SHUTDOWN reason to be fired
        """
        RESTPOSTRequest(self, "system/shutdown",  {},
                        self._syncthing_cb_shutdown, None, Daemon.SHUTDOWN).start()

    def syncing(self):
        """ Returns true if any folder is being synchronized right now  """
        return len(self._syncing_folders) > 0

    def get_api_key(self):
        """ Returns API key used for communication with daemon. May return None """
        return self._api_key

    def get_min_version(self):
        """
        Returns minimal syncthing daemon version that daemon instance
        can handle.
        """
        return MIN_VERSION

    def get_syncing_list(self):
        """
        Returns list of ids of foldersitories that are being
        synchronized right now.
        """
        return list(self._syncing_folders)

    def get_my_id(self):
        """
        Returns ID of device that is instance connected to.
        May return None to indicate that ID is not yet known
        """
        return self._my_id

    def get_version(self):
        """
        Returns daemon version or "unknown" if daemon version is not yet
        known
        """
        if self._my_id == None:
            return "unknown"
        device = self._get_device_data(self._my_id)
        if "clientVersion" in device:
            return device["clientVersion"]
        return "unknown"

    def get_webui_url(self):
        """ Returns web ui url in http(s)://127.0.0.1:8080 format """
        return "%s://%s" % (
            "https" if self._tls else "http",
            self._address
        )

    def get_address(self):
        """ Returns tuple address on which daemon listens on. """
        return self._address

    def is_connected(self):
        """ Returns True if daemon is known to be alive """
        return self._connected

    def pause(self, device_id):
        """ Pauses synchronization with specified device """
        RESTPOSTRequest(self, "system/pause?device=%s" % (device_id,),
                        {}, lambda *a: a, lambda *a: log.error(a), device_id).start()

    def resume(self, device_id):
        """ Resumes synchronization with specified device """
        RESTPOSTRequest(self, "system/resume?device=%s" % (device_id,),
                        {}, lambda *a: a, lambda *a: log.error(a), device_id).start()

    def rescan(self, folder_id, path=None):
        """ Asks daemon to rescan entire folder or specified path """
        if path is None:
            id_enc = urllib.parse.quote(folder_id.encode('utf-8'))
            RESTPOSTRequest(self, "db/scan?folder=%s" % (id_enc,), {},
                            lambda *a: a, lambda *a: log.error(a), folder_id).start()
        else:
            url = "db/scan?folder=%s&sub=%s" % (
                urllib.parse.quote(folder_id.encode('utf-8')),
                urllib.parse.quote(path.encode('utf-8'))
            )
            RESTPOSTRequest(self, url, {}, lambda *a: a,
                            lambda *a: log.error(a), folder_id).start()

    def override(self, folder_id):
        """ Asks daemon to override remote changes made in specified folder """
        id_enc = urllib.parse.quote(folder_id.encode('utf-8'))
        RESTPOSTRequest(self, "db/override?folder=%s" % (id_enc,), {},
                        lambda *a: a, lambda *a: log.error(a), folder_id).start()

    def revert(self, folder_id):
        """ Asks daemon to revert local changes made in specified folder """
        id_enc = urllib.quote(folder_id.encode('utf-8'))
        RESTPOSTRequest(self, "db/revert?folder=%s" % (id_enc,), {},
                        lambda *a: a, lambda *a: log.error(a), folder_id).start()

    def request_events(self):
        """
        No longer needed.
        """
        pass

    def set_refresh_interval(self, i):
        """ Sets interval used mainly by event querying timer """
        self._refresh_interval = i
        log.verbose("Set refresh interval to %s", i)


if __name__ == "__main__":
    # Small thing for testing
    from .tools import init_logging, set_logging_level
    init_logging()
    set_logging_level(True, True)
    daemon = Daemon()
    daemon.connect(
        'connected', lambda *a: sys.stdout.write("*** connected ***\n"))
    daemon.connect(
        'disconnected', lambda *a: sys.stdout.write("*** disconnected ***\n"))
    daemon.reconnect()
    GLib.MainLoop().run()
