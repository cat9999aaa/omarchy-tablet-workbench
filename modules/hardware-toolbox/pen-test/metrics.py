"""Privacy-safe aggregates for the pen diagnostic; no ink coordinates."""
import math
class Metrics:
 def __init__(self):
  self.events=0; self.contacts=0; self.sources={}; self.axes={k:None for k in ('pressure','xtilt','ytilt')}
 def add(self,source,contact,axes):
  self.events+=1; self.contacts+=int(contact); self.sources[source]=self.sources.get(source,0)+1
  for key in self.axes:
   value=axes.get(key)
   if value is None or not math.isfinite(value):continue
   old=self.axes[key];self.axes[key]=[value,value] if old is None else [min(old[0],value),max(old[1],value)]
 def summary(self):
  return {'events':self.events,'contacts':self.contacts,'sources':dict(self.sources),'axes':{k:list(v) if v is not None else None for k,v in self.axes.items()}}
