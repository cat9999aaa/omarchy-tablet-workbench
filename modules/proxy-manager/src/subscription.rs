use crate::legacy::run_bounded;
use std::time::Duration;
pub fn validate_url(value:&str)->Result<(),String>{
 if value.len()>2048||value.chars().any(char::is_control){return Err("invalid_subscription_url".into());}
 let u=url::Url::parse(value).map_err(|_|"invalid_subscription_url")?;
 if u.scheme()!="https"||u.host_str().is_none()||!u.username().is_empty()||u.password().is_some()||u.fragment().is_some(){return Err("https_subscription_required".into());}Ok(())
}
pub fn download(value:&str)->Result<Vec<u8>,String>{
 validate_url(value)?;
 // Curl config arrives over stdin so bearer URL is not in process arguments.
 let config=format!("url = {}\n",serde_json::to_string(value).map_err(|_|"invalid_subscription_url")?);
 run_bounded(&["/usr/bin/curl","--config","-","--proto","=https","--max-time","20","--max-redirs","0","--max-filesize","8388608","--fail","--silent"].iter().map(|s|s.to_string()).collect::<Vec<_>>(),config.as_bytes(),Duration::from_secs(23),8*1024*1024).map_err(|_|"subscription_download_failed".into())
}
