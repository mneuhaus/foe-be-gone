

Hof Neuhaus / Dream Machine Pro - Control PlaneHof Neuhaus / Dream Machine Pro[Network](https://unifi.ui.com/consoles/D021F98B48D9000000000654A4A60000000006A0475800000000623C7915:843489420/network/default)[Protect](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/protect)EAInformation about applicationgetGet application informationViewer information & managementgetGet viewer detailspatchPatch viewer settingsgetGet all viewersLive view managementgetGet live view detailspatchPatch live view configurationgetGet all live viewspostCreate live viewWebSocket updatesgetGet update messages about devicesgetGet Protect event messagesCamera PTZ control & managementpostStart a camera PTZ patrolpostStop active camera PTZ patrolpostMove PTZ camera to presetAlarm manager integrationpostSend a webhook to the alarm managerLight information & managementgetGet light detailspatchPatch light settingsgetGet all lightsCamera information & managementgetGet camera detailspatchPatch camera settingsgetGet all cameraspostCreate RTSPS streams for cameradelDelete camera RTSPS streamgetGet RTSPS streams for cameragetGet camera snapshotpostPermanently disable camera microphonepostCreate talkback session for cameraSensor information & managementgetGet sensor detailspatchPatch sensor settingsgetGet all sensorsNVR information & managementgetGet NVR detailsDevice asset file managementpostUpload device asset filegetGet device asset filesChime information & managementgetGet chime detailspatchPatch chime settingsgetGet all chimes[API docs by Redocly](https://redocly.com/redoc/)
# UniFi Protect API (5.3.48)

Download OpenAPI specification:[Download](blob:https://unifi.ui.com/6406dfa6-5790-4cf8-bb05-e2c967d081b1)


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Information-about-application)Information about application


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Information-about-application/paths/~1v1~1meta~1info/get)Get application information

Get generic information about the Protect application



### Responses

200 Success response


default Error response


get/v1/meta/infohttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/meta/info
### Response samples

200defaultContent typeapplication/jsonCopy{"applicationVersion": "1.0.0"}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Viewer-information-and-management)Viewer information & management


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Viewer-information-and-management/paths/~1v1~1viewers~1{id}/get)Get viewer details

Get detailed information about a specific viewer



##### path Parameters

idrequiredstring (viewerId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of viewer



### Responses

200 Success response


default Error response


get/v1/viewers/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/viewers/{id}
### Response samples

200defaultContent typeapplication/jsonCopy{"id": "66d025b301ebc903e80003ea","modelKey": "viewer","state": "CONNECTED","name": "string","liveview": "66d025b301ebc903e80003ea","streamLimit": 0}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Viewer-information-and-management/paths/~1v1~1viewers~1{id}/patch)Patch viewer settings

Patch the settings for a specific viewer



##### path Parameters

idrequiredstring (viewerId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of viewer



##### Request Body schema: application/jsonrequired

namestring (name)  The name of the model


liveviewliveviewId (string) or null
### Responses

200 Success response


default Error response


patch/v1/viewers/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/viewers/{id}
### Request samples

PayloadContent typeapplication/jsonCopy{"name": "string","liveview": "66d025b301ebc903e80003ea"}
### Response samples

200defaultContent typeapplication/jsonCopy{"id": "66d025b301ebc903e80003ea","modelKey": "viewer","state": "CONNECTED","name": "string","liveview": "66d025b301ebc903e80003ea","streamLimit": 0}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Viewer-information-and-management/paths/~1v1~1viewers/get)Get all viewers

Get detailed information about all viewers



### Responses

200 Success response


default Error response


get/v1/viewershttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/viewers
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all [{"id": "66d025b301ebc903e80003ea","modelKey": "viewer","state": "CONNECTED","name": "string","liveview": "66d025b301ebc903e80003ea","streamLimit": 0}]
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Live-view-management)Live view management


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Live-view-management/paths/~1v1~1liveviews~1{id}/get)Get live view details

Get detailed information about a specific live view



##### path Parameters

idrequiredstring (liveviewId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of liveview



### Responses

200 Success response


default Error response


get/v1/liveviews/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/liveviews/{id}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "liveview","name": "string","isDefault": true,"isGlobal": true,"owner": "66d025b301ebc903e80003ea","layout": 1,"slots": [{"cameras": ["66d025b301ebc903e80003ea"],"cycleMode": "motion","cycleInterval": 0}]}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Live-view-management/paths/~1v1~1liveviews~1{id}/patch)Patch live view configuration

Patch the configuration about a specific live view



##### path Parameters

idrequiredstring (liveviewId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of liveview



##### Request Body schema: application/jsonrequired

idrequiredstring (liveviewId)  The primary key of liveview


modelKeyrequiredstring (liveviewModelKey)  The model key of the liveview


 Value:  "liveview"namerequiredstring The name of this live view.


isDefaultrequiredboolean Whether this live view is the default one for all viewers.


isGlobalrequiredboolean Whether this live view is global and available system-wide to all users


ownerrequiredstring (userId)  The primary key of user


layoutrequirednumber  [ 1 .. 26 ]  The number of slots this live view contains. Which as a consequence also affects the layout of the live view.


slotsrequiredArray of objects List of cameras visible in each given slot. And cycling settings for each slot if it has multiple cameras listed.



### Responses

200 Success response


default Error response


patch/v1/liveviews/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/liveviews/{id}
### Request samples

PayloadContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "liveview","name": "string","isDefault": true,"isGlobal": true,"owner": "66d025b301ebc903e80003ea","layout": 1,"slots": [{"cameras": ["66d025b301ebc903e80003ea"],"cycleMode": "motion","cycleInterval": 0}]}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "liveview","name": "string","isDefault": true,"isGlobal": true,"owner": "66d025b301ebc903e80003ea","layout": 1,"slots": [{"cameras": ["66d025b301ebc903e80003ea"],"cycleMode": "motion","cycleInterval": 0}]}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Live-view-management/paths/~1v1~1liveviews/get)Get all live views

Get detailed information about all live views



### Responses

200 Success response


default Error response


get/v1/liveviewshttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/liveviews
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all [{"id": "66d025b301ebc903e80003ea","modelKey": "liveview","name": "string","isDefault": true,"isGlobal": true,"owner": "66d025b301ebc903e80003ea","layout": 1,"slots": [{"cameras": ["66d025b301ebc903e80003ea"],"cycleMode": "motion","cycleInterval": 0}]}]
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Live-view-management/paths/~1v1~1liveviews/post)Create live view

Create a new live view



##### Request Body schema: application/jsonrequired

idrequiredstring (liveviewId)  The primary key of liveview


modelKeyrequiredstring (liveviewModelKey)  The model key of the liveview


 Value:  "liveview"namerequiredstring The name of this live view.


isDefaultrequiredboolean Whether this live view is the default one for all viewers.


isGlobalrequiredboolean Whether this live view is global and available system-wide to all users


ownerrequiredstring (userId)  The primary key of user


layoutrequirednumber  [ 1 .. 26 ]  The number of slots this live view contains. Which as a consequence also affects the layout of the live view.


slotsrequiredArray of objects List of cameras visible in each given slot. And cycling settings for each slot if it has multiple cameras listed.



### Responses

200 Success response


default Error response


post/v1/liveviewshttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/liveviews
### Request samples

PayloadContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "liveview","name": "string","isDefault": true,"isGlobal": true,"owner": "66d025b301ebc903e80003ea","layout": 1,"slots": [{"cameras": ["66d025b301ebc903e80003ea"],"cycleMode": "motion","cycleInterval": 0}]}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "liveview","name": "string","isDefault": true,"isGlobal": true,"owner": "66d025b301ebc903e80003ea","layout": 1,"slots": [{"cameras": ["66d025b301ebc903e80003ea"],"cycleMode": "motion","cycleInterval": 0}]}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/WebSocket-updates)WebSocket updates


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/WebSocket-updates/paths/~1v1~1subscribe~1devices/get)Get update messages about devices

A WebSocket subscription which broadcasts all changes happening to Protect-managed hardware devices



### Responses

200 Success response


default Error response


get/v1/subscribe/deviceshttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/subscribe/devices
### Response samples

200defaultContent typeapplication/jsonExampleaddupdateremoveaddCopy Expand all  Collapse all {"type": "add","item": {"id": "66d025b301ebc903e80003ea","modelKey": "nvr","name": "string","doorbellSettings": {"defaultMessageText": "string","defaultMessageResetTimeoutMs": 0,"customMessages": ["string"],"customImages": [{"preview": "string","sprite": "string"}]}}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/WebSocket-updates/paths/~1v1~1subscribe~1events/get)Get Protect event messages

A WebSocket subscription that broadcasts Protect events



### Responses

200 Success response


default Error response


get/v1/subscribe/eventshttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/subscribe/events
### Response samples

200defaultContent typeapplication/jsonExampleaddupdateaddCopy Expand all  Collapse all {"type": "add","item": {"id": "66d025b301ebc903e80003ea","modelKey": "event","type": "ring","start": 1445408038748,"end": 1445408048748,"device": "66d025b301ebc903e80003ea"}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-PTZ-control-and-management)Camera PTZ control & management


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-PTZ-control-and-management/paths/~1v1~1cameras~1{id}~1ptz~1patrol~1start~1{slot}/post)Start a camera PTZ patrol

Start a camera PTZ patrol



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera


slotrequiredstring (activePatrolSlotString)   Examples: 0 1 2 3 4 The slot number (0-4) of the patrol that is currently running, or null if no patrol is running



### Responses

204 The camera PTZ patrol was started successfully.


default Error response


post/v1/cameras/{id}/ptz/patrol/start/{slot}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}/ptz/patrol/start/{slot}
### Response samples

defaultContent typeapplication/jsonCopy Expand all  Collapse all {"error": "Unexpected API error occurred","name": "API_ERROR","cause": {"error": "Unexpected functionality error","name": "UNKNOWN_ERROR"}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-PTZ-control-and-management/paths/~1v1~1cameras~1{id}~1ptz~1patrol~1stop/post)Stop active camera PTZ patrol

Stop active camera PTZ patrol



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera



### Responses

204 The camera PTZ patrol was stopped successfully.


default Error response


post/v1/cameras/{id}/ptz/patrol/stophttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}/ptz/patrol/stop
### Response samples

defaultContent typeapplication/jsonCopy Expand all  Collapse all {"error": "Unexpected API error occurred","name": "API_ERROR","cause": {"error": "Unexpected functionality error","name": "UNKNOWN_ERROR"}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-PTZ-control-and-management/paths/~1v1~1cameras~1{id}~1ptz~1goto~1{slot}/post)Move PTZ camera to preset

Adjust the PTZ camera position to a specified preset



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera


slotrequiredstring  Examples: -1 0 2 8 9 The slot number (0-4) of the preset to move the camera to



### Responses

204 The PTZ camera was moved to the given preset successfully.


default Error response


post/v1/cameras/{id}/ptz/goto/{slot}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}/ptz/goto/{slot}
### Response samples

defaultContent typeapplication/jsonCopy Expand all  Collapse all {"error": "Unexpected API error occurred","name": "API_ERROR","cause": {"error": "Unexpected functionality error","name": "UNKNOWN_ERROR"}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Alarm-manager-integration)Alarm manager integration


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Alarm-manager-integration/paths/~1v1~1alarm-manager~1webhook~1{id}/post)Send a webhook to the alarm manager

Send a webhook to the alarm manager to trigger configured alarms



##### path Parameters

idrequiredstring (alarmTriggerId)   Examples: AnyRandomString User defined string used to trigger only specific alarms. Alarm should be configured with the same ID to be triggered.



### Responses

204 Webhook was sent to alarm manager successfully


400 Bad request response


post/v1/alarm-manager/webhook/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/alarm-manager/webhook/{id}
### Response samples

400Content typeapplication/jsonCopy Expand all  Collapse all {"error": "'id' is required","name": "BAD_REQUEST","cause": {"error": "Unexpected functionality error","name": "UNKNOWN_ERROR"}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Light-information-and-management)Light information & management


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Light-information-and-management/paths/~1v1~1lights~1{id}/get)Get light details

Get detailed information about a specific light



##### path Parameters

idrequiredstring (lightId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of light



### Responses

200 Success response


default Error response


get/v1/lights/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/lights/{id}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "light","state": "CONNECTED","name": "string","lightModeSettings": {"mode": "always","enableAt": "fulltime"},"lightDeviceSettings": {"isIndicatorEnabled": true,"pirDuration": 0,"pirSensitivity": 100,"ledLevel": 1},"isDark": true,"isLightOn": true,"isLightForceEnabled": true,"lastMotion": 0,"isPirMotionDetected": true,"camera": "66d025b301ebc903e80003ea"}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Light-information-and-management/paths/~1v1~1lights~1{id}/patch)Patch light settings

Patch the settings for a specific light



##### path Parameters

idrequiredstring (lightId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of light



##### Request Body schema: application/jsonrequired

namestring (name)  The name of the model


isLightForceEnabledboolean (isLightForceEnabled)  Whether the light has its main LED currently force-enabled.


lightModeSettingsobject (lightModeSettings)  Settings for when and how your light gets activated


lightDeviceSettingsobject (lightDeviceSettings)  Hardware settings for light device.



### Responses

200 Success response


default Error response


patch/v1/lights/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/lights/{id}
### Request samples

PayloadContent typeapplication/jsonCopy Expand all  Collapse all {"name": "string","isLightForceEnabled": true,"lightModeSettings": {"mode": "always","enableAt": "fulltime"},"lightDeviceSettings": {"isIndicatorEnabled": true,"pirDuration": 0,"pirSensitivity": 100,"ledLevel": 1}}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "light","state": "CONNECTED","name": "string","lightModeSettings": {"mode": "always","enableAt": "fulltime"},"lightDeviceSettings": {"isIndicatorEnabled": true,"pirDuration": 0,"pirSensitivity": 100,"ledLevel": 1},"isDark": true,"isLightOn": true,"isLightForceEnabled": true,"lastMotion": 0,"isPirMotionDetected": true,"camera": "66d025b301ebc903e80003ea"}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Light-information-and-management/paths/~1v1~1lights/get)Get all lights

Get detailed information about all lights



### Responses

200 Success response


default Error response


get/v1/lightshttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/lights
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all [{"id": "66d025b301ebc903e80003ea","modelKey": "light","state": "CONNECTED","name": "string","lightModeSettings": {"mode": "always","enableAt": "fulltime"},"lightDeviceSettings": {"isIndicatorEnabled": true,"pirDuration": 0,"pirSensitivity": 100,"ledLevel": 1},"isDark": true,"isLightOn": true,"isLightForceEnabled": true,"lastMotion": 0,"isPirMotionDetected": true,"camera": "66d025b301ebc903e80003ea"}]
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-information-and-management)Camera information & management


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-information-and-management/paths/~1v1~1cameras~1{id}/get)Get camera details

Get detailed information about a specific camera



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera



### Responses

200 Success response


default Error response


get/v1/cameras/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "camera","state": "CONNECTED","name": "string","isMicEnabled": true,"osdSettings": {"isNameEnabled": true,"isDateEnabled": true,"isLogoEnabled": true,"isDebugEnabled": true},"ledSettings": {"isEnabled": true},"lcdMessage": {"type": "LEAVE_PACKAGE_AT_DOOR","resetAt": 0,"text": "string"},"micVolume": 100,"activePatrolSlot": 0,"videoMode": "default","hdrType": "auto","featureFlags": {"supportFullHdSnapshot": true,"hasHdr": true,"smartDetectTypes": ["person"],"smartDetectAudioTypes": ["alrmSmoke"],"videoModes": ["default"],"hasMic": true,"hasLedStatus": true,"hasSpeaker": true},"smartDetectSettings": {"objectTypes": ["person"],"audioTypes": ["alrmSmoke"]}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-information-and-management/paths/~1v1~1cameras~1{id}/patch)Patch camera settings

Patch the settings for a specific camera



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera



##### Request Body schema: application/jsonrequired

namestring The name of the camera


osdSettingsobject (osdSettings)  On Screen Display settings.


ledSettingsobject (ledSettings)  LED settings.


lcdMessagelcdMessage (object) or lcdMessage (object) or lcdMessage (object) or lcdMessage (object) (lcdMessage)  micVolumenumber (micVolume)   [ 0 .. 100 ]  Mic volume: a number from 0-100.


videoModestring (videoMode)  Enum: "default" "highFps" "sport" "slowShutter"  Current video mode of the camera


hdrTypestring (videoMode)  Enum: "auto" "on" "off"  High Dynamic Range (HDR) mode setting.


smartDetectSettingsobject (smartDetectSettings)  Smart detection settings for the camera.



### Responses

200 Success response


default Error response


patch/v1/cameras/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}
### Request samples

PayloadContent typeapplication/jsonCopy Expand all  Collapse all {"name": "string","osdSettings": {"isNameEnabled": true,"isDateEnabled": true,"isLogoEnabled": true,"isDebugEnabled": true},"ledSettings": {"isEnabled": true},"lcdMessage": {"type": "DO_NOT_DISTURB","resetAt": 0},"micVolume": 100,"videoMode": "default","hdrType": "auto","smartDetectSettings": {"objectTypes": ["person"],"audioTypes": ["alrmSmoke"]}}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "camera","state": "CONNECTED","name": "string","isMicEnabled": true,"osdSettings": {"isNameEnabled": true,"isDateEnabled": true,"isLogoEnabled": true,"isDebugEnabled": true},"ledSettings": {"isEnabled": true},"lcdMessage": {"type": "LEAVE_PACKAGE_AT_DOOR","resetAt": 0,"text": "string"},"micVolume": 100,"activePatrolSlot": 0,"videoMode": "default","hdrType": "auto","featureFlags": {"supportFullHdSnapshot": true,"hasHdr": true,"smartDetectTypes": ["person"],"smartDetectAudioTypes": ["alrmSmoke"],"videoModes": ["default"],"hasMic": true,"hasLedStatus": true,"hasSpeaker": true},"smartDetectSettings": {"objectTypes": ["person"],"audioTypes": ["alrmSmoke"]}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-information-and-management/paths/~1v1~1cameras/get)Get all cameras

Get detailed information about all cameras



### Responses

200 Success response


default Error response


get/v1/camerashttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all [{"id": "66d025b301ebc903e80003ea","modelKey": "camera","state": "CONNECTED","name": "string","isMicEnabled": true,"osdSettings": {"isNameEnabled": true,"isDateEnabled": true,"isLogoEnabled": true,"isDebugEnabled": true},"ledSettings": {"isEnabled": true},"lcdMessage": {"type": "LEAVE_PACKAGE_AT_DOOR","resetAt": 0,"text": "string"},"micVolume": 100,"activePatrolSlot": 0,"videoMode": "default","hdrType": "auto","featureFlags": {"supportFullHdSnapshot": true,"hasHdr": true,"smartDetectTypes": ["person"],"smartDetectAudioTypes": ["alrmSmoke"],"videoModes": ["default"],"hasMic": true,"hasLedStatus": true,"hasSpeaker": true},"smartDetectSettings": {"objectTypes": ["person"],"audioTypes": ["alrmSmoke"]}}]
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-information-and-management/paths/~1v1~1cameras~1{id}~1rtsps-stream/post)Create RTSPS streams for camera

Returns RTSPS stream URLs for specified quality levels



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera



##### Request Body schema: application/jsonrequired

qualitiesrequiredArray of strings (createdQualities)   non-empty Items Enum: "high" "medium" "low" "package"  Array of quality levels of RTSPS streams



### Responses

200 Success response


default Error response


post/v1/cameras/{id}/rtsps-streamhttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}/rtsps-stream
### Request samples

PayloadContent typeapplication/jsonCopy Expand all  Collapse all {"qualities": ["high","medium"]}
### Response samples

200defaultContent typeapplication/jsonCopy{"high": "rtsps://192.168.1.1:7441/5nPr7RCmueGTKMP7?enableSrtp","medium": "rtsps://192.168.1.1:7441/AbUgnDb5IqIEMidk?enableSrtp"}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-information-and-management/paths/~1v1~1cameras~1{id}~1rtsps-stream/delete)Delete camera RTSPS stream

Remove the RTSPS stream for a specified camera



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera



##### query Parameters

qualitiesrequiredArray of removedQualities (strings) or channelQuality (string) (removedQualities)   Examples: qualities=high&qualities=medium The array of quality levels for the RTSPS streams to be removed.



### Responses

204 RTSPS stream successfully removed


default Error response


delete/v1/cameras/{id}/rtsps-streamhttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}/rtsps-stream
### Response samples

defaultContent typeapplication/jsonCopy Expand all  Collapse all {"error": "Unexpected API error occurred","name": "API_ERROR","cause": {"error": "Unexpected functionality error","name": "UNKNOWN_ERROR"}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-information-and-management/paths/~1v1~1cameras~1{id}~1rtsps-stream/get)Get RTSPS streams for camera

Returns existing RTSPS stream URLs for camera



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera



### Responses

200 Success response


default Error response


get/v1/cameras/{id}/rtsps-streamhttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}/rtsps-stream
### Response samples

200defaultContent typeapplication/jsonCopy{"high": "rtsps://192.168.1.1:7441/5nPr7RCmueGTKMP7?enableSrtp","medium": "rtsps://192.168.1.1:7441/AbUgnDb5IqIEMidk?enableSrtp","low": null,"package": null}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-information-and-management/paths/~1v1~1cameras~1{id}~1snapshot/get)Get camera snapshot

Get a snapshot image from a specific camera



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera



##### query Parameters

highQualitystring (forceHighQuality)  Default:  "false" Enum: "true" "false"  Whether to force 1080P or higher resolution snapshot



### Responses

200 Camera snapshot


default Error response


get/v1/cameras/{id}/snapshothttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}/snapshot
### Response samples

defaultContent typeapplication/jsonCopy Expand all  Collapse all {"error": "Unexpected API error occurred","name": "API_ERROR","cause": {"error": "Unexpected functionality error","name": "UNKNOWN_ERROR"}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-information-and-management/paths/~1v1~1cameras~1{id}~1disable-mic-permanently/post)Permanently disable camera microphone

Disable the microphone for a specific camera. This action cannot be undone unless the camera is reset.



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera



### Responses

200 Success response


default Error response


post/v1/cameras/{id}/disable-mic-permanentlyhttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}/disable-mic-permanently
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "camera","state": "CONNECTED","name": "string","isMicEnabled": true,"osdSettings": {"isNameEnabled": true,"isDateEnabled": true,"isLogoEnabled": true,"isDebugEnabled": true},"ledSettings": {"isEnabled": true},"lcdMessage": {"type": "LEAVE_PACKAGE_AT_DOOR","resetAt": 0,"text": "string"},"micVolume": 100,"activePatrolSlot": 0,"videoMode": "default","hdrType": "auto","featureFlags": {"supportFullHdSnapshot": true,"hasHdr": true,"smartDetectTypes": ["person"],"smartDetectAudioTypes": ["alrmSmoke"],"videoModes": ["default"],"hasMic": true,"hasLedStatus": true,"hasSpeaker": true},"smartDetectSettings": {"objectTypes": ["person"],"audioTypes": ["alrmSmoke"]}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Camera-information-and-management/paths/~1v1~1cameras~1{id}~1talkback-session/post)Create talkback session for camera

Returns the talkback stream URL and audio configuration for a specific camera



##### path Parameters

idrequiredstring (cameraId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of camera



### Responses

200 Success response



##### Response Schema: application/json

urlrequiredstring <uri>  (talkbackStreamUrl)  Talkback stream URL


codecrequiredstring (talkbackStreamCodec)  Audio format to use.


samplingRaterequiredinteger (talkbackStreamSamplingRate)   > 0  Sampling Rate.


bitsPerSamplerequiredinteger (talkbackStreamBitsPerSample)   > 0  Bits per sample.


default Error response


post/v1/cameras/{id}/talkback-sessionhttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/cameras/{id}/talkback-session
### Response samples

200defaultContent typeapplication/jsonCopy{"url": "rtp://192.168.1.123:7004","codec": "opus","samplingRate": 24000,"bitsPerSample": 16}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Sensor-information-and-management)Sensor information & management


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Sensor-information-and-management/paths/~1v1~1sensors~1{id}/get)Get sensor details

Get detailed information about a specific sensor



##### path Parameters

idrequiredstring (sensorId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of sensor



### Responses

200 Success response


default Error response


get/v1/sensors/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/sensors/{id}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "sensor","state": "CONNECTED","name": "string","mountType": "garage","batteryStatus": {"percentage": 0,"isLow": true},"stats": {"light": {"value": 0,"status": "high"},"humidity": {"value": 0,"status": "high"},"temperature": {"value": 0,"status": "high"}},"lightSettings": {"isEnabled": true,"margin": 0,"lowThreshold": 1,"highThreshold": 0},"humiditySettings": {"isEnabled": true,"margin": 0,"lowThreshold": 1,"highThreshold": 0},"temperatureSettings": {"isEnabled": true,"margin": 0,"lowThreshold": -39,"highThreshold": 0},"isOpened": true,"openStatusChangedAt": 0,"isMotionDetected": true,"motionDetectedAt": 0,"motionSettings": {"isEnabled": true,"sensitivity": 100},"alarmTriggeredAt": 0,"alarmSettings": {"isEnabled": true},"leakDetectedAt": 0,"tamperingDetectedAt": 0}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Sensor-information-and-management/paths/~1v1~1sensors~1{id}/patch)Patch sensor settings

Patch the settings for a specific sensor



##### path Parameters

idrequiredstring (sensorId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of sensor



##### Request Body schema: application/jsonrequired

namestring (name)  The name of the model


lightSettingsobject (lightSettings)  Ambient light sensor settings.


humiditySettingsobject (humiditySettings)  Relative humidity sensor settings.


temperatureSettingsobject (temperatureSettings)  Temperature sensor settings.


motionSettingsobject (motionSettings)  Motion sensor settings.


alarmSettingsobject (alarmSettings)  Smoke and carbon monoxide alarm sensor settings.



### Responses

200 Success response


default Error response


patch/v1/sensors/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/sensors/{id}
### Request samples

PayloadContent typeapplication/jsonCopy Expand all  Collapse all {"name": "string","lightSettings": {"isEnabled": true,"margin": 0,"lowThreshold": 1,"highThreshold": 0},"humiditySettings": {"isEnabled": true,"margin": 0,"lowThreshold": 1,"highThreshold": 0},"temperatureSettings": {"isEnabled": true,"margin": 0,"lowThreshold": -39,"highThreshold": 0},"motionSettings": {"isEnabled": true,"sensitivity": 100},"alarmSettings": {"isEnabled": true}}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "sensor","state": "CONNECTED","name": "string","mountType": "garage","batteryStatus": {"percentage": 0,"isLow": true},"stats": {"light": {"value": 0,"status": "high"},"humidity": {"value": 0,"status": "high"},"temperature": {"value": 0,"status": "high"}},"lightSettings": {"isEnabled": true,"margin": 0,"lowThreshold": 1,"highThreshold": 0},"humiditySettings": {"isEnabled": true,"margin": 0,"lowThreshold": 1,"highThreshold": 0},"temperatureSettings": {"isEnabled": true,"margin": 0,"lowThreshold": -39,"highThreshold": 0},"isOpened": true,"openStatusChangedAt": 0,"isMotionDetected": true,"motionDetectedAt": 0,"motionSettings": {"isEnabled": true,"sensitivity": 100},"alarmTriggeredAt": 0,"alarmSettings": {"isEnabled": true},"leakDetectedAt": 0,"tamperingDetectedAt": 0}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Sensor-information-and-management/paths/~1v1~1sensors/get)Get all sensors

Get detailed information about all sensors



### Responses

200 Success response


default Error response


get/v1/sensorshttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/sensors
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all [{"id": "66d025b301ebc903e80003ea","modelKey": "sensor","state": "CONNECTED","name": "string","mountType": "garage","batteryStatus": {"percentage": 0,"isLow": true},"stats": {"light": {"value": 0,"status": "high"},"humidity": {"value": 0,"status": "high"},"temperature": {"value": 0,"status": "high"}},"lightSettings": {"isEnabled": true,"margin": 0,"lowThreshold": 1,"highThreshold": 0},"humiditySettings": {"isEnabled": true,"margin": 0,"lowThreshold": 1,"highThreshold": 0},"temperatureSettings": {"isEnabled": true,"margin": 0,"lowThreshold": -39,"highThreshold": 0},"isOpened": true,"openStatusChangedAt": 0,"isMotionDetected": true,"motionDetectedAt": 0,"motionSettings": {"isEnabled": true,"sensitivity": 100},"alarmTriggeredAt": 0,"alarmSettings": {"isEnabled": true},"leakDetectedAt": 0,"tamperingDetectedAt": 0}]
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/NVR-information-and-management)NVR information & management


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/NVR-information-and-management/paths/~1v1~1nvrs/get)Get NVR details

Get detailed information about the NVR



### Responses

200 Success response


default Error response


get/v1/nvrshttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/nvrs
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "nvr","name": "string","doorbellSettings": {"defaultMessageText": "string","defaultMessageResetTimeoutMs": 0,"customMessages": ["string"],"customImages": [{"preview": "string","sprite": "string"}]}}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Device-asset-file-management)Device asset file management


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Device-asset-file-management/paths/~1v1~1files~1{fileType}/post)Upload device asset file

Upload a new device asset file



##### path Parameters

fileTyperequiredstring (assetFileType)  Value: "animations"  Device asset file type



##### Request Body schema: multipart/form-data

string <binary>  A binary file with one of these MIME types: image/gif, image/jpeg, image/png, audio/mpeg, audio/mp4, audio/wave, audio/x-caf}



### Responses

200 Processed and persisted device asset


default Error response


post/v1/files/{fileType}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/files/{fileType}
### Response samples

200defaultContent typeapplication/jsonCopy{"name": "string","type": "animations","originalName": "string","path": "string"}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Device-asset-file-management/paths/~1v1~1files~1{fileType}/get)Get device asset files

Get a list of all device asset files



##### path Parameters

fileTyperequiredstring (assetFileType)  Value: "animations"  Device asset file type



### Responses

200 Device asset list


default Error response


get/v1/files/{fileType}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/files/{fileType}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all [{"name": "string","type": "animations","originalName": "string","path": "string"}]
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Chime-information-and-management)Chime information & management


## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Chime-information-and-management/paths/~1v1~1chimes~1{id}/get)Get chime details

Get detailed information about a specific chime



##### path Parameters

idrequiredstring (chimeId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of chime



### Responses

200 Success response


default Error response


get/v1/chimes/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/chimes/{id}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "chime","state": "CONNECTED","name": "string","cameraIds": ["66d025b301ebc903e80003ea"],"ringSettings": [{"cameraId": "string","repeatTimes": 1,"ringtoneId": "string","volume": 100}]}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Chime-information-and-management/paths/~1v1~1chimes~1{id}/patch)Patch chime settings

Patch the settings for a specific chime



##### path Parameters

idrequiredstring (chimeId)   Examples: 66d025b301ebc903e80003ea 672094f900e26303e800062a The primary key of chime



##### Request Body schema: application/jsonrequired

namestring The name of the chime


cameraIdsArray of strings (cameraId)  The list of (doorbell-only) cameras which this chime is paired to.


ringSettingsArray of objects (ringSettings)  List of custom ringtone settings for (doorbell-only) cameras paired to this chime.



### Responses

200 Success response


default Error response


patch/v1/chimes/{id}https://YOUR_CONSOLE_IP/proxy/protect/integration/v1/chimes/{id}
### Request samples

PayloadContent typeapplication/jsonCopy Expand all  Collapse all {"name": "string","cameraIds": ["66d025b301ebc903e80003ea"],"ringSettings": [{"cameraId": "string","repeatTimes": 1,"ringtoneId": "string","volume": 100}]}
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all {"id": "66d025b301ebc903e80003ea","modelKey": "chime","state": "CONNECTED","name": "string","cameraIds": ["66d025b301ebc903e80003ea"],"ringSettings": [{"cameraId": "string","repeatTimes": 1,"ringtoneId": "string","volume": 100}]}
## [](https://unifi.ui.com/consoles/AC8BA944E5380000000006FD3DD5000000000751567200000000637B9151:1446127353/unifi-api/protect#tag/Chime-information-and-management/paths/~1v1~1chimes/get)Get all chimes

Get detailed information about all chimes



### Responses

200 Success response


default Error response


get/v1/chimeshttps://YOUR_CONSOLE_IP/proxy/protect/integration/v1/chimes
### Response samples

200defaultContent typeapplication/jsonCopy Expand all  Collapse all [{"id": "66d025b301ebc903e80003ea","modelKey": "chime","state": "CONNECTED","name": "string","cameraIds": ["66d025b301ebc903e80003ea"],"ringSettings": [{"cameraId": "string","repeatTimes": 1,"ringtoneId": "string","volume": 100}]}]