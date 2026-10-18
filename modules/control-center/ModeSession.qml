// SPDX-License-Identifier: GPL-3.0-only
import QtQuick
import Quickshell.Io
import "ModeProtocol.js" as Protocol

QtObject {
    id: root
    property var observerCommand: []
    property var sampleCommand: []
    property bool sessionOpen: false
    property bool outputEligible: false
    property string choice: "auto"
    property var lastEffective: null
    property string health: "unknown"
    property string reason: "closed"
    property int generation: 0
    property int requestSequence: 0
    property double observerSeq: -1
    property bool observerReady: false
    property var observer: null
    property var request: null
    property var pending: null
    property bool dirty: false
    property bool restartPending: false
    property int round: 0
    property bool confirming: false
    property int samplesUsed: 0
    readonly property bool busy: request !== null || debounce.running || confirm.running
    readonly property bool isStopped: observer === null && request === null
    signal modeSuggested(string mode)
    signal stopped()
    onIsStoppedChanged: if(isStopped) { stopped(); Qt.callLater(pump) }

    function validChoice(value) { return ["auto","tablet","desktop"].indexOf(value)>=0 }
    function begin(eligible, selection, effective) {
        if (!isStopped || sessionOpen || !validChoice(selection)) return false
        outputEligible=eligible===true;lastEffective=["tablet","desktop"].indexOf(effective)>=0?effective:null
        sessionOpen=true;choose(selection);return true
    }
    function reset() {
        generation++;pending=null;dirty=false;observerReady=false;observerSeq=-1
        debounce.stop();confirm.stop();startup.stop();samplesUsed=0;round=0;confirming=false
        if(request)request.cancel()
        if(observer)observer.cancel()
    }
    function choose(selection) {
        if(!sessionOpen || !validChoice(selection))return
        choice=selection;restartPending=false;reset()
        if(choice!=="auto") { health="observed";reason="manual";lastEffective=choice;modeSuggested(choice);return }
        if(!outputEligible) { health="unavailable";reason="output_unavailable";return }
        health="unknown";reason="starting";restartPending=true;pump()
    }
    function refresh() { if(sessionOpen)choose(choice) }
    function close() {
        sessionOpen=false;restartPending=false;reset();health="unknown";reason="closed"
        if(isStopped)stopped()
    }
    function fail(code) {
        restartPending=false;reset();health="unavailable";reason=code
    }
    function pump() {
        if(!sessionOpen || choice!=="auto" || !outputEligible)return
        if(restartPending) {
            if(!isStopped)return
            restartPending=false
            observer=observerFactory.createObject(root,{epoch:generation})
            if(!observer){fail("observer_failed");return}
            observer.running=true;startup.start();return
        }
        if(!observerReady || !dirty || debounce.running || confirm.running || request!==null)return
        if(samplesUsed>=4){dirty=false;return}
        dirty=false;samplesUsed++;requestSequence++
        request=requestFactory.createObject(root,{epoch:generation,seq:observerSeq,token:requestSequence,
            payload:JSON.stringify({choice:choice,last_effective:lastEffective,pending:pending})})
        if(!request){fail("read_failed");return}
        request.running=true
    }
    function trigger() {
        if(!sessionOpen || !observerReady || choice!=="auto")return
        health="unknown";reason="refreshing"
        pending=null;dirty=true;round=0;confirming=false;samplesUsed=0;confirm.stop()
        if(request)request.cancel()
        debounce.restart()
    }
    function receive(child, chunk) {
        if(child!==observer || child.epoch!==generation || !sessionOpen)return
        const value=Protocol.feed(child.buffer,chunk,observerSeq)
        if(!value.valid){fail("invalid_notice");return}
        child.buffer=value.buffer;observerSeq=value.seq
        for(const event of value.events) {
            if(event==="ready") {observerReady=true;startup.stop();trigger()}
            else if(event==="changed")trigger()
            else {fail("observer_lost");return}
        }
    }
    function accept(child, text, code) {
        if(child.cancelled || child.epoch!==generation || child.seq!==observerSeq || child.token!==requestSequence
            || !sessionOpen || !observerReady || choice!=="auto")return
        const value=code===0?Protocol.response(text):null
        if(!value){fail("read_failed");return}
        pending=value.mode.pending;health=value.mode.health;reason=value.mode.reason_code
        if(health==="observed" && value.mode.effective!==null) {
            lastEffective=value.mode.effective;modeSuggested(lastEffective);return
        }
        if(value.confirm_after_ms!==null && !confirming) {
            confirming=true;confirm.interval=Math.max(1,value.confirm_after_ms);confirm.start();return
        }
        if(round===0) {
            round=1;confirming=false;pending=null;dirty=true;Qt.callLater(pump)
        }
    }
    property Timer debounce: Timer { interval:100;onTriggered:root.pump() }
    property Timer confirm: Timer { onTriggered:{root.dirty=true;root.pump()} }
    property Timer startup: Timer { interval:3000;onTriggered:root.fail("observer_timeout") }
    property Component observerFactory: Component {
        Process {
            id:child
            required property int epoch
            property string buffer: ""
            property bool cancelled:false
            property bool started:false
            property bool disposed:false
            command:root.observerCommand
            function cancel() {cancelled=true;if(running)signal(15);reap.start()}
            function dispose() {
                if(disposed)return
                disposed=true;reap.stop()
                if(root.observer===child)root.observer=null
                destroy();Qt.callLater(root.pump)
            }
            stdout:SplitParser {splitMarker:"";onRead:data=>root.receive(child,data)}
            onStarted:started=true
            onExited:function(code,status) {
                if(!cancelled && epoch===root.generation && root.sessionOpen)root.fail("observer_exited")
                dispose()
            }
            onRunningChanged:if(!running && !started)Qt.callLater(function(){
                if(!disposed && !running && !started){if(epoch===root.generation)root.fail("observer_failed");dispose()}
            })
            property Timer reap:Timer {interval:500;onTriggered:{if(child.running){child.signal(9);restart()}else child.dispose()}}
        }
    }
    property Component requestFactory: Component {
        Process {
            id:child
            required property int epoch
            required property double seq
            required property int token
            required property string payload
            property bool cancelled:false
            property bool started:false
            property bool disposed:false
            property bool streamDone:false
            property bool exitSeen:false
            property int code:-1
            command:root.sampleCommand
            stdinEnabled:true
            function cancel() {cancelled=true;deadline.stop();if(running)signal(15);reap.start()}
            function dispose() {
                if(disposed)return
                disposed=true;deadline.stop();reap.stop()
                if(root.request===child)root.request=null
                destroy();Qt.callLater(root.pump)
            }
            function finish() {
                if(disposed || !streamDone || !exitSeen)return
                root.accept(child,output.text,code);dispose()
            }
            onStarted:{started=true;write(payload);stdinEnabled=false}
            stdout:StdioCollector {
                id:output;waitForEnd:false
                onDataChanged:if(Protocol.size(text)>65536){root.fail("oversize_response");child.cancel()}
                onStreamFinished:{child.streamDone=true;child.finish()}
            }
            onExited:function(exitCode,exitStatus){code=exitStatus===0?exitCode:-1;exitSeen=true;finish()}
            onRunningChanged:if(!running && !started)Qt.callLater(function(){
                if(!disposed && !running && !started){if(epoch===root.generation)root.fail("read_failed");dispose()}
            })
            property Timer deadline:Timer {interval:6000;running:true;onTriggered:{root.fail("read_timeout");child.cancel()}}
            property Timer reap:Timer {interval:500;onTriggered:{if(child.running){child.signal(9);restart()}else child.dispose()}}
        }
    }
    Component.onDestruction:{if(request)request.signal(9);if(observer)observer.signal(9)}
}
