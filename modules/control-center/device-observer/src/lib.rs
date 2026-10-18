// SPDX-License-Identifier: GPL-3.0-only
use std::io::{self, Write};
pub mod udev;

pub enum InputNotice { Ready, Changed, Lost }
pub struct Notifier<W: Write> { writer: W, started: bool, ended: bool, seq: u64 }
impl<W: Write> Notifier<W> {
    pub fn new(writer: W) -> Self { Self { writer, started:false, ended:false, seq:0 } }
    /// True means the session can continue. Lost is always terminal.
    pub fn send(&mut self, notice: InputNotice) -> io::Result<bool> {
        if self.ended { return Ok(false); }
        let event = match notice {
            InputNotice::Ready if !self.started => { self.started=true; "ready" },
            InputNotice::Changed if self.started => "changed",
            InputNotice::Lost => { self.ended=true; "lost" },
            _ => return Ok(false),
        };
        let event = if self.seq >= 9_007_199_254_740_991 { self.ended=true; "lost" } else { event };
        writeln!(self.writer,"{{\"schema_version\":1,\"event\":\"{}\",\"seq\":{}}}", event,self.seq)?;
        self.writer.flush()?;
        self.seq+=1;
        Ok(!self.ended)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn sequence_limit_is_terminal_loss() {
        let mut n=Notifier::new(Vec::new());n.started=true;n.seq=9_007_199_254_740_991;
        assert!(!n.send(InputNotice::Changed).unwrap());
        assert_eq!(String::from_utf8(n.writer).unwrap(),"{\"schema_version\":1,\"event\":\"lost\",\"seq\":9007199254740991}\n");
    }
}
