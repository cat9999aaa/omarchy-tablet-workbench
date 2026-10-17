import QtQuick
import QtTest
import "../qml"
Item {
 width: 300; height: 200
 property int count: 0
 property int clears: 0
 TouchKey { id: key; width: 160; height: 100; label: "⌫"; repeatKey: true; onTriggered: count++; onClearTriggered: clears++ }
 Flickable { id: list; x:0;y:110;width:220;height:80;contentHeight:300;clip:true
  TouchKey { id:listKey;width:180;height:55;triggerOnRelease:true;label:"删除";onTriggered:count++ }
 }
 TestCase {
  name: "TouchKeyLifecycle"; when: windowShown
  function init() { count=0; clears=0;key.clearGesture=true; key.inputActive=true; key.enabled=true;key.triggerOnRelease=false;list.contentY=0 }
  function test_hold_and_release() {
   mousePress(key,30,30); wait(560); verify(count>=2); mouseRelease(key,30,30)
   var n=count;wait(180);compare(count,n)
  }
  function test_focus_or_hide_stops_repeat() {
   mousePress(key,30,30);wait(500);key.inputActive=false
   var n=count;wait(200);compare(count,n);mouseRelease(key,30,30)
  }
  function test_generation_change_stops_until_new_press() {
   key.inputGeneration=7;mousePress(key,30,30);wait(500)
   key.inputGeneration=8;var n=count;wait(200);compare(count,n)
   mouseRelease(key,30,30);mouseClick(key,30,30);compare(count,n+1)
  }
  function test_release_action_does_not_fire_on_press() {
   key.triggerOnRelease=true;mousePress(key,30,30);compare(count,0)
   mouseRelease(key,30,30);compare(count,1);key.triggerOnRelease=false
  }
  function test_list_scroll_does_not_delete() {
   mousePress(listKey,30,30);compare(count,0)
   mouseMove(listKey,30,15,30);mouseMove(listKey,30,-30,30);mouseRelease(listKey,30,-30)
   compare(count,0)
  }
  function test_hold_swipe_clear_once() {
   mousePress(key,80,80);wait(480);mouseMove(key,80,15,30)
   verify(key.clearArmed);var n=count;wait(180);compare(count,n)
   mouseRelease(key,80,15);compare(clears,1);wait(120);compare(clears,1)
  }
  function test_swipe_back_cancels_clear() {
   mousePress(key,80,80);wait(480);mouseMove(key,80,15,30)
   verify(key.clearArmed);mouseMove(key,80,80,30);verify(!key.clearArmed)
   mouseRelease(key,80,80);compare(clears,0)
  }
  function test_fast_swipe_does_not_clear() {
   mousePress(key,80,80);mouseMove(key,80,15,20);mouseRelease(key,80,15);compare(clears,0)
  }
  function test_swipe_focus_change_cancels() {
   mousePress(key,80,80);wait(480);mouseMove(key,80,15,30)
   key.inputGeneration++;mouseRelease(key,80,15);compare(clears,0)
  }
  function test_armed_disable_or_hide_cancels() {
   mousePress(key,80,80);wait(480);mouseMove(key,80,15,30);verify(key.clearArmed)
   key.enabled=false;mouseRelease(key,80,15);compare(clears,0);key.enabled=true
   mousePress(key,80,80);wait(480);mouseMove(key,80,15,30);key.visible=false
   mouseRelease(key,80,15);compare(clears,0);key.visible=true
  }
  function test_horizontal_exit_cancels() {
   mousePress(key,80,80);wait(480);mouseMove(key,80,15,30);verify(key.clearArmed)
   mouseMove(key,-20,15,30);verify(!key.clearArmed);mouseRelease(key,-20,15);compare(clears,0)
  }
  function test_inactive_no_action() {
   key.inputActive=false;mouseClick(key,30,30);compare(count,0)
  }
 }
}
