"""Keep the product's injected Wi-Fi content; substitute device/action boundaries."""
# SPDX-License-Identifier: GPL-3.0-only
import json
import re


def wifi_source(source, block):
    lines = source.splitlines(keepends=True)
    properties = []
    for index, line in enumerate(lines):
        if re.match(r'^  (readonly )?property ', line):
            end = index + 1
            while end < len(lines) and not re.match(r'^  [A-Za-z/]', lines[end]):
                end += 1
            properties.append(''.join(lines[index:end]).rstrip())
    actions = {'close', 'toggleNetwork', 'setScannerEnabled', 'copyToClipboard',
               'summonWifiQr', 'refresh', 'setBand', 'summonSpeedTest', 'setDns',
               'runNetworkAction', 'connectDirectly', 'connectWithPassphrase',
               'connectEnterprise', 'disconnect', 'disconnectRow', 'forget'}
    methods = []
    for name in re.findall(r'^  function (\w+)\(', source, re.M):
        if name in actions:
            methods.append('function '+name+'(){actions=actions.concat([{operation:'+json.dumps(name)+'}])}')
        else:
            methods.append(block(source, '  function '+name+'('))
    body = block(source, '      Column { width: parent.width; spacing: Style.space(12)')
    body = body.replace('Column { width:', 'Column { id:wifiColumn; width:', 1)
    components = '\n'.join(block(source, '  component '+name+':') for name in
                           ['BandPill', 'DnsProviderPill', 'NetworkRow', 'DetailValue', 'InfoLabel', 'InfoValue'])
    qml = '''import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.Commons
import qs.Ui
import "NetworkModel.js" as Model
import "Workbench/Theme.js" as Theme
import "Workbench" as WB
Item {
 id:root
 implicitHeight:wifiColumn.implicitHeight
 property var bar:({foreground:Color.foreground,urgent:Color.urgent,fontFamily:Style.font.family})
 property var networking:({backend:"NetworkManager",wifiEnabled:true,devices:{values:[]}})
 property var actions:[]
 property bool opened:false
'''+ '\n'.join(properties+methods)+ '\n'+body+'\n'+components+'\n}\n'
    qml = qml.replace('Networking.', 'networking.')
    qml = re.sub(r'\b(?:NetworkBackendType|DeviceType|WifiSecurityType|ConnectionFailReason)\.(\w+)',
                 lambda match: json.dumps(match.group(1)), qml)
    # Names only expose the original input/target objects to the matrix.
    for name in ('networkList', 'rowMouse', 'rightMouse', 'idField', 'pwField', 'connectPwBtn', 'bandHeader', 'bandAutoRow'):
        qml = qml.replace('id: '+name+'\n', 'id: '+name+';objectName:"wifi-'+name+'"\n')
    return qml
