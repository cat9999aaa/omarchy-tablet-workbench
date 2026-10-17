"""Pure touchscreen recognizer. Coordinates exist only for the current gesture."""
class ThreeFingerSwipe:
    def __init__(self):self.reset()
    def reset(self):
        self.first=None;self.start=None;self.last={};self.ids=set();self.blocked=False
    def frame(self, contacts, now):
        if not contacts:
            fire=False
            if self.start is not None and not self.blocked and .08<=now-self.first<=1.5:
                moves=[(self.last[i][0]-self.start[i][0],self.last[i][1]-self.start[i][1]) for i in self.ids]
                fire=all(dy>=.08 and abs(dx)<=.08 and dy>abs(dx)*1.7 for dx,dy in moves)
            self.reset();return fire
        if self.first is None:self.first=now
        if len(contacts)>3:self.blocked=True
        if self.start is None and len(contacts)==3:
            if now-self.first>.3:self.blocked=True
            self.start=dict(contacts);self.ids=set(contacts);self.last=dict(contacts)
        if self.start is not None:
            if not set(contacts)<=self.ids:self.blocked=True
            self.last.update({i:p for i,p in contacts.items() if i in self.ids})
        return False


class TouchFrames:
    """Type-B multitouch protocol decoder, including persistent per-slot axes."""
    def __init__(self,xmin,xmax,ymin,ymax):
        self.bounds=(xmin,xmax,ymin,ymax);self.slot=0;self.slots={};self.dropped=False;self.model=ThreeFingerSwipe()
    def event(self,kind,code,value,now):
        if kind==0 and code==3:
            self.dropped=True;self.slots={};self.model.reset();return False
        if self.dropped:
            if kind==0 and code==0:self.dropped=False
            return False
        if kind==3:
            if code==47:self.slot=value
            elif code==57:self.slots.setdefault(self.slot,{})['id']=value if value>=0 else None
            elif code in (53,54):self.slots.setdefault(self.slot,{})['x' if code==53 else 'y']=value
        elif kind==0 and code==0:
            xmin,xmax,ymin,ymax=self.bounds
            contacts={d['id']:((d['x']-xmin)/(xmax-xmin),(d['y']-ymin)/(ymax-ymin)) for d in self.slots.values() if d.get('id') is not None and 'x' in d and 'y' in d}
            return self.model.frame(contacts,now)
        return False
