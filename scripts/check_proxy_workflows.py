"""Conservative policy lint, not a replacement for GitHub's workflow parser."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[1]
for path in sorted((root/'.github/workflows').glob('proxy-*.yml')):
 text=path.read_text()
 assert 'contents: read' in text and 'persist-credentials: false' in text
 assert not any(v in text for v in ('pull_request_target','self-hosted','secrets.','write-all','contents: write','issues: write'))
 for action in re.findall(r'uses:\s*([^\s#]+)',text):assert re.fullmatch(r'[A-Za-z0-9_./-]+@[0-9a-f]{40}',action),action
 assert 'timeout-minutes:' in text
 print(path.name+': pinned actions, read-only token, hosted runner, no private secrets')
