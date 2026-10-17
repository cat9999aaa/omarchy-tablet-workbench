import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons

Item {
    id: root
    property var state: ({ visible: false, focused: false, generation: 0, candidates: [], preedit: "", mode: "t9", voicePhase: "idle", voiceText: "", sensitive: false, error: "" })
    property bool uppercase: false
    property bool settingsOpen: false
    readonly property bool inputActive: root.state.visible===true && root.state.focused===true && root.state.voicePhase==="idle"
    property int panelWidth: 440
    readonly property string projectDir: Quickshell.env("HOME") + "/Projects/pcadmin/tools/omarchy-touch-ime"
    SystemPalette { id: palette }
    readonly property color bg: Color.background
    readonly property color fg: Color.foreground
    readonly property color buttonBg: Qt.lighter(Color.background,1.45)
    readonly property color accent: Color.accent
    function send(action) {
        if (!backend.running) return
        action.generation = root.state.generation || 0
        backend.write(JSON.stringify(action) + "\n")
    }
    function key(name) { send({op: "key", key: name}) }
    function mode(name) { uppercase = false; send({op: "mode", mode: name}) }
    IpcHandler {
        target: "omtInput"
        function toggle(): void { root.send({op: "toggle"}) }
        function show(): void { root.send({op: "show"}) }
        function hide(): void { root.send({op: "hide"}) }
        function version(): string { return "0.2.3" }
        function ready(): bool { return backend.running && (root.state.generation || 0) > 0 }
    }
    Process {
        id: backend
        command: [root.projectDir + "/build/omt-backend",
                  root.projectDir + "/rime",
                  Quickshell.env("HOME") + "/.local/share/pcadmin-touch-ime/rime"]
        stdinEnabled: true
        running: true
        stdout: SplitParser { onRead: line => { try { root.state = JSON.parse(line) } catch (_) {} } }
        onExited: { root.state = Object.assign({}, root.state, {visible: false, error: "输入服务已停止"}) }
    }
    PanelWindow {
        id: panel
        visible: root.state.visible === true
        anchors { top: true; bottom: true; right: true }
        implicitWidth: root.panelWidth
        exclusiveZone: width
        color: root.bg
        WlrLayershell.namespace: "pcadmin-touch-ime"
        WlrLayershell.layer: WlrLayer.Top
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

        ColumnLayout {
            id: inputLayout
            anchors.fill: parent; anchors.margins: 10; spacing: 6
            Text { text: "Omarchy 输入"; color: root.fg; font.pixelSize: 20; Layout.fillWidth: true }


            Text {
                Layout.fillWidth: true; wrapMode: Text.Wrap; color: root.fg; font.pixelSize: 13
                text: root.state.error || (root.state.sensitive ? "密码输入 · 中文与语音已关闭" : root.state.focused ? root.state.mode==="handwriting" ? "一次写一个字，点候选输入" : "点候选输入 · P1 或底部收起" : "请先点一下要输入的文字框")
            }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: root.settingsOpen ? 210 : 65
                color: root.buttonBg; radius: 10; border.width: 1; border.color: Qt.rgba(root.fg.r,root.fg.g,root.fg.b,0.12)
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 6
                    Text { visible: root.state.editingPhrase===true; Layout.fillWidth: true; text: "短语："+(root.state.phraseDraft||"请用下方键盘输入"); color: root.fg; font.pixelSize: 18; elide: Text.ElideLeft }


                    VoicePreview {
                        visible: !root.settingsOpen && (root.state.voicePhase!=="idle" || !!root.state.voiceText)
                        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 65
                        foreground: root.fg; backgroundColor: root.bg
                        value: root.state.voicePhase==="recording" ? "● 正在听… 点停止结束" : root.state.voicePhase==="stopping"||root.state.voicePhase==="transcribing" ? "正在离线识别…" : root.state.voiceText||"没有识别到内容"
                    }
                    ColumnLayout {
                        visible: root.settingsOpen; Layout.fillWidth: true
                        Text { text: "本地词库 · 点短语即可输入"; color: root.fg; font.pixelSize: 20 }
                        TouchKey { label: root.state.learning===false ? "常用词学习：已暂停" : "常用词学习：已开启"; Layout.fillWidth: true; Layout.preferredHeight: 46; foreground: root.fg; baseColor: root.bg; accentColor: root.accent; onTriggered: root.send({op:"learning",enabled:root.state.learning===false}) }
                        TouchKey { label: "备份个人词库"; Layout.fillWidth: true; Layout.preferredHeight: 46; foreground: root.fg; baseColor: root.bg; accentColor: root.accent; onTriggered: root.send({op:"dictionaryBackup"}) }
                        TouchKey { label: "添加常用短语"; Layout.fillWidth: true; Layout.preferredHeight: 42; fontSize: 16; foreground: root.fg; baseColor: root.bg; accentColor: root.accent; enabled: root.state.focused; onTriggered: {root.settingsOpen=false;root.send({op:"phraseStart"})} }
                        TouchKey { visible: !!root.state.preedit; label: "忘记首个候选词"; Layout.fillWidth: true; Layout.preferredHeight: 42; fontSize: 16; foreground: root.fg; baseColor: root.bg; accentColor: root.accent; onTriggered: root.send({op:"forget",index:0,preedit:root.state.preedit,page:root.state.page}) }
                        Flickable {
                            Layout.fillWidth: true; Layout.preferredHeight: Math.min(130,phraseList.implicitHeight); contentHeight: phraseList.implicitHeight; clip: true
                            Column {
                                id: phraseList; width: parent.width; spacing: 4
                                Repeater {
                                    model: root.state.phrases||[]
                                    RowLayout {
                                        required property string modelData; width: phraseList.width; spacing: 6
                                        TouchKey { label: parent.modelData; Layout.fillWidth: true; Layout.preferredHeight: 40; fontSize: 15; triggerOnRelease: true; foreground: root.fg; baseColor: root.bg; accentColor: root.accent; inputGeneration: root.state.generation||0; inputActive: root.inputActive; onTriggered: {root.send({op:"text",text:parent.modelData});root.settingsOpen=false} }
                                        TouchKey { label: "删除"; Layout.preferredWidth: 56; Layout.preferredHeight: 40; fontSize: 14; triggerOnRelease: true; foreground: root.fg; baseColor: root.bg; accentColor: root.accent; inputGeneration: root.state.generation||0; inputActive: root.inputActive; onTriggered: root.send({op:"phraseDelete",text:parent.modelData}) }
                                    }
                                }
                            }
                        }
                        Text { Layout.fillWidth: true; text: root.state.notice||"只保存在本机，不上传云端"; color: root.fg; font.pixelSize: 13; wrapMode: Text.Wrap }
                    }
                    Item { Layout.fillHeight: true; Layout.minimumHeight: 0 }

                }
            }

            RowLayout {
                objectName: "editToolbar"; Layout.fillWidth: true; spacing: 4
                Repeater {
                    model: [{label:"全选",key:"Control+a"},{label:"剪切",key:"Control+x"},{label:"复制",key:"Control+c"},{label:"粘贴",key:"Control+v"},{label:"◀",key:"Left"},{label:"▶",key:"Right"}]
                    TouchKey { required property var modelData; label: modelData.label; fontSize: 15; Layout.fillWidth: true; Layout.preferredHeight: 48; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; inputActive: root.inputActive; enabled: root.inputActive && !root.state.preedit && !root.state.editingVoice && !root.state.editingPhrase && (!root.state.sensitive || modelData.key==="Control+v" || modelData.key==="Left" || modelData.key==="Right"); onTriggered: root.key(modelData.key) }
                }
            }
            ColumnLayout {
                objectName: "candidateArea"; Layout.fillWidth: true; spacing: 4; visible: !root.settingsOpen
                Text { Layout.fillWidth: true; color: root.fg; font.pixelSize: 20; elide: Text.ElideLeft; text: root.state.preedit ? (root.state.mode==="t9" ? "拼音组合 · " : "")+root.state.preedit : root.state.mode==="t9" ? "九键拼音 · 点字母组，再选字" : ""; visible: !!text }
                    GridLayout {
                        visible: !root.settingsOpen && (root.state.candidates||[]).length>0
                        Layout.fillWidth: true; columns: 3; columnSpacing: 5; rowSpacing: 5
                        Repeater {
                            model: root.state.candidates||[]
                            TouchKey {
                                required property string modelData; required property int index
                                Layout.fillWidth: true; Layout.preferredHeight: 46
                                label: modelData.length>6 ? modelData.slice(0,6)+"…" : modelData
                                foreground: root.fg; baseColor: index===0 ? Qt.lighter(root.buttonBg,1.35) : root.bg; accentColor: root.accent
                                inputActive: root.inputActive
                                onTriggered: {root.send({op:"choose",index:index,preedit:root.state.preedit,page:root.state.page,revision:root.state.handwritingRevision});if(root.state.mode==="handwriting")handPad.reset()}
                            }
                        }
                    }
                    RowLayout {
                        visible: !root.settingsOpen && (root.state.candidates||[]).length>0 && root.state.mode!=="handwriting"
                        Layout.fillWidth: true
                        TouchKey { label: "上一页"; Layout.fillWidth: true; Layout.preferredHeight: 34; fontSize: 15; foreground: root.fg; baseColor: root.bg; accentColor: root.accent; enabled: root.state.page>0; onTriggered: root.send({op:"page",next:false}) }
                        Text { text: String((root.state.page||0)+1); color: root.fg }
                        TouchKey { label: "下一页"; Layout.fillWidth: true; Layout.preferredHeight: 34; fontSize: 15; foreground: root.fg; baseColor: root.bg; accentColor: root.accent; enabled: !root.state.lastPage; onTriggered: root.send({op:"page",next:true}) }
                    }
            }
            GridLayout {
                objectName: "t9Keys"
                visible: !root.settingsOpen && (root.state.mode==="t9"); Layout.fillWidth: true
                columns: 4; columnSpacing: 6; rowSpacing: 6
                Repeater {
                    model: ["分词","ABC","DEF","GHI","JKL","MNO","PQRS","TUV","WXYZ"]
                    TouchKey {
                        required property string modelData; required property int index
                        Layout.row: Math.floor(index/3); Layout.column: index%3
                        Layout.fillWidth: true; Layout.preferredHeight: 64
                        label: modelData; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; inputActive: root.inputActive
                        enabled: root.inputActive
                        onTriggered: root.key(index===0 ? "'" : String(index+1))
                    }
                }
                TouchKey { objectName: "t9Backspace"; label: "⌫"; fontSize: 28; repeatKey: true; inputGeneration: root.state.generation||0; Layout.row: 0; Layout.column: 3; Layout.rowSpan: 2; Layout.preferredWidth: 74; Layout.fillHeight: true; Layout.minimumHeight: 134; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; inputActive: root.inputActive; enabled: root.inputActive; onTriggered: root.key("BackSpace") }
                TouchKey { label: "回车"; Layout.row: 2; Layout.column: 3; Layout.preferredWidth: 74; Layout.preferredHeight: 64; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; inputActive: root.inputActive; enabled: root.inputActive; onTriggered: root.key("Return") }
            }
            ColumnLayout {
                visible: !root.settingsOpen && (root.state.mode==="abc"||root.state.mode==="pinyin")
                Layout.fillWidth: true; spacing: 6
                KeyRow { objectName: "digitRow"; labels: ["1","2","3","4","5","6","7","8","9","0"]; keyHeight: 44; Layout.fillWidth: true; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; inputActive: root.inputActive; onSelected: value => root.send({op:"text",text:value}) }
                KeyRow { labels: ["@",".","/","_","-"]; keyHeight: 38; Layout.fillWidth: true; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; inputActive: root.inputActive; onSelected: value => root.send({op:"text",text:value}) }
                Repeater {
                    model: root.uppercase ? ["QWERTYUIOP","ASDFGHJKL","ZXCVBNM"] : ["qwertyuiop","asdfghjkl","zxcvbnm"]
                    KeyRow { required property string modelData; Layout.fillWidth: true; labels: modelData.split(""); keyHeight: 50; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; inputActive: root.inputActive; onSelected: value => root.key(value) }
                }
            }
            GridLayout {
                visible: !root.settingsOpen && (root.state.mode==="number"||root.state.mode==="symbols"); Layout.fillWidth: true
                columns: root.state.mode==="number" ? 3 : 5; rowSpacing: 5; columnSpacing: 5
                Repeater {
                    model: root.state.mode==="number" ? ["1","2","3","4","5","6","7","8","9",".","0","-"] : ["，","。","？","！","、","：","；","@","(",")","[","]","/","\\","_","-","+","=","\"","'"]
                    TouchKey { required property string modelData; Layout.fillWidth: true; Layout.preferredHeight: 50; label: modelData; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; inputActive: root.inputActive; enabled: root.inputActive; onTriggered: root.send({op:"text",text:modelData}) }
                }
            }
            HandwritingPad { id: handPad; visible: !root.settingsOpen && (root.state.mode==="handwriting"); Layout.fillWidth: true; Layout.preferredHeight: 230; foreground: root.fg; background: root.buttonBg; enabled: root.inputActive && !root.state.sensitive; generation: root.state.generation||0; onRecognize: (strokes,w,h,revision) => root.send({op:"handwriting",strokes:strokes,width:w,height:h,revision:revision}); onRevisionChanged: root.send({op:"handwritingClear",revision:revision}) }
            RowLayout {
                Layout.fillWidth: true; spacing: 6
                TouchKey { visible: root.state.mode!=="t9"; label: "⌫"; repeatKey: true; inputGeneration: root.state.generation||0; Layout.preferredWidth: 64; Layout.preferredHeight: 52; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; inputActive: root.inputActive; enabled: root.inputActive; onTriggered: root.key("BackSpace") }
                TouchKey { label: root.state.mode==="abc" ? "⇧" : "，"; Layout.preferredWidth: 48; Layout.preferredHeight: 52; foreground: root.fg; baseColor: root.state.mode==="abc"&&root.uppercase ? root.accent : root.buttonBg; accentColor: root.accent; enabled: root.inputActive; onTriggered: {if(root.state.mode==="abc")root.uppercase=!root.uppercase;else root.send({op:"text",text:"，"})} }
                TouchKey { label: "空格"; Layout.fillWidth: true; Layout.preferredHeight: 52; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; enabled: root.inputActive; onTriggered: root.key("space") }
                TouchKey { visible: !root.settingsOpen && (root.state.mode==="t9"); label: "。"; Layout.preferredWidth: 64; Layout.preferredHeight: 52; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; enabled: root.inputActive; onTriggered: root.send({op:"text",text:"。"}) }
                TouchKey { visible: root.state.mode!=="t9"; label: "回车"; Layout.preferredWidth: 74; Layout.preferredHeight: 52; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; enabled: root.inputActive; onTriggered: root.key("Return") }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 4
                Repeater {
                    model: [{label:"九键",mode:"t9"},{label:"全拼",mode:"pinyin"},{label:"英文",mode:"abc"},{label:"123",mode:"number"},{label:"符号",mode:"symbols"},{label:"手写",mode:"handwriting"}]
                    TouchKey {
                        required property var modelData
                        Layout.fillWidth: true; Layout.preferredHeight: 48; fontSize: 16
                        label: modelData.label; foreground: root.state.mode===modelData.mode ? root.bg : root.fg
                        baseColor: root.state.mode===modelData.mode ? root.accent : root.buttonBg; accentColor: root.accent
                        enabled: root.state.focused && !(root.state.sensitive && (modelData.mode==="t9"||modelData.mode==="pinyin"||modelData.mode==="handwriting"))
                        onTriggered: {root.settingsOpen=false;root.mode(modelData.mode)}
                    }
                }
            }
            RowLayout {
                Layout.fillWidth: true; spacing: 6
                TouchKey { label: "清空组合"; Layout.preferredWidth: 90; Layout.preferredHeight: 42; fontSize: 15; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; onTriggered: root.send({op:"clear"}) }
                TouchKey { visible: !!root.state.voiceText; label: root.state.editingVoice ? "完成修改" : "修改预览"; Layout.preferredWidth: 80; Layout.preferredHeight: 42; fontSize: 14; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; onTriggered: root.send({op:"voiceEdit"}) }
                TouchKey { visible: !root.state.editingPhrase; label: root.state.voicePhase==="recording" ? "停止录音" : "语音"; Layout.fillWidth: true; Layout.preferredHeight: 42; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; enabled: root.state.focused&&!root.state.sensitive&&(root.state.voicePhase==="idle"||root.state.voicePhase==="recording"); onTriggered: root.send({op:"voice"}) }
                TouchKey { visible: root.state.editingPhrase===true; label: "取消"; Layout.preferredWidth: 65; Layout.preferredHeight: 42; fontSize: 15; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; onTriggered: root.send({op:"phraseCancel"}) }
                TouchKey { visible: root.state.editingPhrase===true; label: "保存短语"; Layout.fillWidth: true; Layout.preferredHeight: 42; fontSize: 16; foreground: root.bg; baseColor: root.accent; accentColor: root.buttonBg; enabled: !!root.state.phraseDraft; onTriggered: root.send({op:"phraseSave"}) }
                TouchKey { visible: !!root.state.voiceText; label: "输入文字"; Layout.preferredWidth: 88; Layout.preferredHeight: 42; fontSize: 15; foreground: root.bg; baseColor: root.accent; accentColor: root.buttonBg; enabled: root.state.focused; onTriggered: root.send({op:"voiceCommit"}) }
            }
            RowLayout { Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                TouchKey { label: "设置"; Layout.preferredWidth: 56; Layout.preferredHeight: 42; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; enabled: !root.state.sensitive; onTriggered: root.settingsOpen=!root.settingsOpen }
                TouchKey { label: "收起 ↓"; Layout.preferredWidth: 90; Layout.preferredHeight: 42; foreground: root.fg; baseColor: root.buttonBg; accentColor: root.accent; onTriggered: {root.settingsOpen=false;root.send({op:"hide"})} }
            }
        }
    }
}
