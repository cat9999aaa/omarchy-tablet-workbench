import QtQuick
import QtTest
import "../../ui" as Proxy
TestCase {
 id:test; name:"NativeProxy";visible:true;when:windowShown;width:1280;height:1280
 Component {id:ui;Proxy.Main{}}
 function test_geometry_data(){return [{tag:"small",w:640,h:604},{tag:"landscape",w:1280,h:800},{tag:"portrait",w:800,h:1280}]}
 function test_geometry(row){
  let p=createTemporaryObject(ui,test,{width:row.w,height:row.h});verify(p!==null)
  for(let i=0;i<7;i++){p.choosePage(i);wait(30);compare(p.page,i);compare(p.width,row.w);compare(p.height,row.h);let body=findChild(p,"pageBody");verify(body!==null);let pos=body.mapToItem(p,0,0);verify(pos.x>=0&&pos.y>=0);verify(pos.x+body.width<=p.width+.1);verify(pos.y+body.height<=p.height+.1);let close=findChild(p,"closeProxy");verify(close.height>=48);let pt=close.mapToItem(p,0,0);verify(pt.y+close.height<=p.height);}
  p.choosePage(0);wait(20);let button=findChild(p,"proxyToggle");verify(button!==null);verify(button.height>=48);grabImage(p).save("/work/proxy-ui-"+row.tag+".png")
 }
 function test_unknown_is_not_connected(){let p=createTemporaryObject(ui,test);compare(p.model.online,false);compare(p.model.physicalLabel,"未知");p.model.accept({error_code:"service_unavailable"});compare(p.model.online,false);}
 function test_close_does_not_disable(){let p=createTemporaryObject(ui,test);let sent=0,closed=0;p.model.requested.connect(function(){sent++});p.closeRequested.connect(function(){closed++});p.requestClose();compare(closed,1);compare(sent,0);}
 function test_draft_navigation_guard(){let p=createTemporaryObject(ui,test);p.model.draft={mode:"global",dirty:true};p.choosePage(2);compare(p.page,0);compare(p.leavePrompt,true);p.discardAndContinue();compare(p.page,2);compare(p.model.draft.dirty,false);}
 function test_busy_single_submission(){let p=createTemporaryObject(ui,test);p.model.snapshot={revision:5,capabilities:["enable"]};let sent=0;p.model.requested.connect(function(){sent++});p.model.submit("enable",true);p.model.submit("enable",true);compare(sent,1);verify(p.model.pending);}
 function test_stale_response_cannot_replace_new(){let p=createTemporaryObject(ui,test);p.model.accept({snapshot:{revision:10,capabilities:[]}});p.model.accept({snapshot:{revision:9,capabilities:["enable"]}});compare(p.model.snapshot.revision,10);}
 function test_node_and_route_changes_are_drafts(){let p=createTemporaryObject(ui,test);let sent=0;p.model.requested.connect(function(){sent++});p.model.selectNode("candidate");p.model.selectMode("global");compare(p.model.draft.node_id,"candidate");compare(p.model.draft.mode,"global");verify(p.model.draft.dirty);compare(sent,0);}
 function test_catalog_preview_needs_explicit_commit(){let p=createTemporaryObject(ui,test);let calls=[];p.model.catalogRequested.connect(function(v){calls.push(v)});p.model.acceptCatalog({preview_id:"abc",nodes:[],diff:{added:1}});compare(calls.length,0);p.model.commitPreview(true);compare(calls.length,1);compare(calls[0].action,"commit");}
 function test_large_catalog_uses_virtual_list(){let p=createTemporaryObject(ui,test,{width:640,height:604});let nodes=[];for(let i=0;i<1000;i++)nodes.push({id:"n"+i,name:"测试节点"+i,protocol:"VLESS",transport:"tcp / reality",status:"待实测"});p.model.catalog={nodes:nodes,revision:1};p.choosePage(1);wait(30);let list=findChild(p,"nodeList");verify(list!==null);compare(list.count,1000);verify(list.itemAtIndex(999)===null);}
}
