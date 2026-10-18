use serde::{Serialize,Deserialize};
use sha2::{Sha256,Digest};
use base64::Engine;
use std::collections::{BTreeMap,BTreeSet};
#[derive(Clone,Copy)]pub enum ImportFormat{Uri,Base64,LegacyJson}
/// Private representation. Never derive Debug or put it in a public IPC response.
#[derive(Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Node{
 pub id:String,pub name:String,pub server:String,pub port:u16,pub credential:String,
 pub security:String,pub transport:String,pub path:String,pub host:String,pub sni:String,
 pub fingerprint:String,pub public_key:String,pub short_id:String,pub spider_x:String,pub flow:String,pub alpn:Vec<String>
}
#[derive(Clone,Serialize,Deserialize)]pub struct PublicNode{pub id:String,pub name:String,pub protocol:String,pub transport:String,pub status:String}
#[derive(Serialize,Deserialize)]pub struct ImportPreview{pub nodes:Vec<Node>}
#[derive(Serialize)]pub struct ImportDiff{pub added:usize,pub removed:usize,pub retained:usize,pub current_removed:bool}
impl ImportPreview{pub fn public(&self)->Vec<PublicNode>{self.nodes.iter().map(|n|PublicNode{id:n.id.clone(),name:n.name.clone(),protocol:"VLESS".into(),transport:format!("{} / {}",n.transport,n.security),status:"待实测".into()}).collect()}}
fn uuid(s:&str)->bool{s.len()==36&&s.bytes().enumerate().all(|(i,b)|if [8,13,18,23].contains(&i){b==b'-'}else{b.is_ascii_hexdigit()})}
fn clean(s:&str)->bool{s.len()<=2048&&!s.chars().any(char::is_control)}
fn decoded(s:&str)->Result<String,String>{
 let bytes=s.as_bytes();let mut out=Vec::new();let mut i=0;
 while i<bytes.len(){if bytes[i]==b'%'{if i+2>=bytes.len(){return Err("invalid_encoding".into());}let hex=std::str::from_utf8(&bytes[i+1..i+3]).map_err(|_|"invalid_encoding")?;let n=u8::from_str_radix(hex,16).map_err(|_|"invalid_encoding")?;out.push(n);i+=3;}else{out.push(bytes[i]);i+=1;}}
 String::from_utf8(out).map_err(|_|"invalid_encoding".into())
}
impl Node {
 pub fn validate(&mut self)->Result<(),String>{
  if self.port==0||!uuid(&self.credential)||self.server.is_empty()||self.server.len()>253||self.server.chars().any(|c|c.is_whitespace()||"/@?#".contains(c)){return Err("invalid_endpoint".into());}
  if !["tcp","ws"].contains(&self.transport.as_str())||!["tls","reality"].contains(&self.security.as_str()){return Err("unsupported_transport".into());}
  if self.sni.is_empty()||!clean(&self.sni)||self.sni.contains(char::is_whitespace){return Err("tls_name_required".into());}
  if !["","xtls-rprx-vision"].contains(&self.flow.as_str())||(!self.flow.is_empty()&&self.transport!="tcp"){return Err("unsupported_flow".into());}
  if !["","chrome","firefox","safari","edge","ios","android","random","randomized"].contains(&self.fingerprint.as_str()){return Err("unsupported_fingerprint".into());}
  if self.security=="reality" {
   if self.transport!="tcp"||base64::engine::general_purpose::URL_SAFE_NO_PAD.decode(&self.public_key).map(|b|b.len()).unwrap_or(0)!=32||self.short_id.len()>16||self.short_id.len()%2!=0||!self.short_id.bytes().all(|b|b.is_ascii_hexdigit()){return Err("invalid_reality".into());}
  }else if !self.public_key.is_empty()||!self.short_id.is_empty()||!self.spider_x.is_empty(){return Err("unexpected_reality_fields".into());}
  if self.transport=="tcp"&&(!self.path.is_empty()||!self.host.is_empty()){return Err("unsupported_raw_header".into());}
  if ![&self.path,&self.host,&self.spider_x,&self.name].iter().all(|s|clean(s))||self.alpn.iter().any(|s|!["h2","http/1.1"].contains(&s.as_str())){return Err("invalid_field".into());}
  self.name=self.name.chars().take(80).collect();if self.name.is_empty(){self.name="导入节点".into();}
  let mut identity=self.clone();identity.id.clear();identity.name.clear();let bytes=serde_json::to_vec(&identity).map_err(|_|"invalid_node")?;
  self.id=format!("{:x}",Sha256::digest(bytes))[..24].into();Ok(())
 }
}
fn uri_node(line:&str)->Result<Node,String>{
 if line.len()>16384||!clean(line){return Err("invalid_uri".into());}
 let url=url::Url::parse(line).map_err(|_|"invalid_uri")?;
 if url.scheme()!="vless"{return Err("unsupported_protocol".into());}
 if url.password().is_some()||url.path()!=""{return Err("invalid_uri".into());}
 let mut q=BTreeMap::new();
 for(k,v)in url.query_pairs(){if !["type","security","sni","fp","pbk","sid","spx","flow","encryption","path","host","alpn"].contains(&k.as_ref()){return Err("unsupported_field".into());}if q.insert(k.into_owned(),v.into_owned()).is_some(){return Err("duplicate_field".into());}}
 let get=|key:&str|q.get(key).cloned().unwrap_or_default();
 if !["","none"].contains(&get("encryption").as_str()){return Err("unsupported_encryption".into());}
 let server=url.host().ok_or("invalid_endpoint")?.to_string().trim_matches(['[',']']).to_string();
 let transport=match get("type").as_str(){""|"tcp"|"raw"=>"tcp".into(),s=>s.to_owned()};
 let sni=if get("sni").is_empty()&&server.parse::<std::net::IpAddr>().is_err(){server.clone()}else{get("sni")};
 let mut n=Node{id:"".into(),name:decoded(url.fragment().unwrap_or("导入节点"))?,server,port:url.port().ok_or("invalid_port")?,credential:url.username().to_string(),security:get("security"),transport,path:get("path"),host:get("host"),sni,fingerprint:get("fp"),public_key:get("pbk"),short_id:get("sid"),spider_x:get("spx"),flow:get("flow"),alpn:get("alpn").split(',').filter(|s|!s.is_empty()).map(str::to_owned).collect()};
 n.validate()?;Ok(n)
}
pub fn import_preview(bytes:&[u8],format:ImportFormat)->Result<ImportPreview,String>{
 if bytes.len()>8*1024*1024{return Err("import_too_large".into());}
 let mut nodes=match format {
  ImportFormat::LegacyJson=>serde_json::from_slice::<Vec<Node>>(bytes).map_err(|_|"migration_unsupported")?,
  ImportFormat::Base64=>{let compact:Vec<u8>=bytes.iter().copied().filter(|b|!b.is_ascii_whitespace()).collect();let data=base64::engine::general_purpose::STANDARD.decode(&compact).or_else(|_|base64::engine::general_purpose::STANDARD_NO_PAD.decode(&compact)).or_else(|_|base64::engine::general_purpose::URL_SAFE_NO_PAD.decode(&compact)).map_err(|_|"invalid_base64")?;return import_preview(&data,ImportFormat::Uri);},
  ImportFormat::Uri=>{let text=std::str::from_utf8(bytes).map_err(|_|"invalid_encoding")?;let lines:Vec<_>=text.lines().map(str::trim).filter(|l|!l.is_empty()).collect();if lines.len()>4096{return Err("node_limit".into());}let mut result=Vec::new();for line in lines{result.push(uri_node(line)?);}result}
 };
 if nodes.is_empty()||nodes.len()>4096{return Err("empty_or_oversized_catalog".into());}
 let mut ids=BTreeSet::new();for n in &mut nodes{n.validate()?;if !ids.insert(n.id.clone()){return Err("duplicate_node".into());}}
 Ok(ImportPreview{nodes})
}
pub fn preview_replace(new:&ImportPreview,old:&[PublicNode],current:Option<&str>,confirmed:bool)->Result<ImportDiff,String>{
 if new.nodes.is_empty(){return Err("empty_catalog".into());}
 let ids:BTreeSet<_>=new.nodes.iter().map(|n|n.id.as_str()).collect();let oldids:BTreeSet<_>=old.iter().map(|n|n.id.as_str()).collect();
 let current_removed=current.is_some_and(|id|!ids.contains(id));if current_removed&&!confirmed{return Err("current_node_removed".into());}
 Ok(ImportDiff{added:ids.difference(&oldids).count(),removed:oldids.difference(&ids).count(),retained:ids.intersection(&oldids).count(),current_removed})
}
