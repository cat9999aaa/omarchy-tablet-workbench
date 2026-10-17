import QtQuick
import QtTest
import ".." as WB
TestCase {
 visible:true;name:"WorkbenchTouchComponents";when:windowShown;width:480;height:500
 Component {id:buttonComponent;WB.TouchButton {width:140;text:"很长的中文网络操作名称需要换行"}}
 Component {id:headerComponent;WB.PanelHeader {width:320;title:"网络与代理管理";subtitle:"连接状态未知，请等待设备读回"}}
 Component {id:bodyComponent;WB.PanelBody {width:320;height:160;title:"网络中心";Rectangle {width:parent.width;height:1200}}}
 function test_scrolled_panel_keeps_close_reachable() {
  const panel=createTemporaryObject(bodyComponent,this);verify(panel!==null);wait(10)
  const close=findChild(panel,'workbenchClose');verify(close!==null)
  panel.contentY=800;wait(10)
  const position=close.mapToItem(panel,0,0);verify(position.y>=0);verify(position.y+close.height<=panel.height)
  const scroll=findChild(panel,'workbenchScroll');verify(scroll.height>0);verify(scroll.contentHeight>scroll.height)
  let n=0;panel.closeRequested.connect(function(){n++});mouseClick(close,close.width/2,close.height/2);compare(n,1)
 }
 function test_button_target_and_disabled() {
  const b=createTemporaryObject(buttonComponent,this);verify(b!==null);verify(b.height>=48);verify(b.height>=b.contentItem.implicitHeight+b.topPadding+b.bottomPadding)
  let n=0;b.clicked.connect(function(){n++});mouseClick(b,b.width/2,b.height/2);compare(n,1)
  b.enabled=false;mouseClick(b,b.width/2,b.height/2);compare(n,1)
 }
 function test_header_close_remains_reachable() {
  const h=createTemporaryObject(headerComponent,this);verify(h!==null)
  const close=findChild(h,'workbenchClose');verify(close!==null);verify(close.width>=48);verify(close.height>=48)
  let n=0;h.closeRequested.connect(function(){n++})
  for(const w of [320,480,640]){h.width=w;wait(10);verify(close.x>=0);verify(close.x+close.width<=h.width);mouseClick(close,close.width/2,close.height/2)}
  compare(n,3)
 }
}
