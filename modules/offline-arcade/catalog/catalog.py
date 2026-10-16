#!/usr/bin/python3
"""Rebuild the existing arcade playlists from local titles and pictures; never edit ROMs."""
import argparse
import collections
import datetime
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

OVERRIDES = {
    '2020bb':'2020 超级棒球', 'bstars':'棒球之星', 'bstars2':'棒球之星 2',
    'joyjoy':'欢乐气球', 'neopong':'Neo Pong 乒乓球', 'janshin':'雀神传说',
    'zintrckb':'Zintrick 方块大战', 'bangbead':'Bang Bead 弹珠对战',
    'jockeygp':'赛马大奖赛', 'panicbom':'炸弹人方块', 'goalx3':'超级得点王 3',
    'minasan':'大家的麻将教室', 'gururin':'咕噜旋转方块', 'vliner':'V-Liner 拉霸机',
    'neomrdo':'Neo 小丑先生', 'qndream':'梦幻问答', 'flipshot':'Flip Shot 飞盘对战',
    'miexchng':'金钱交换机', 'marukodq':'樱桃小丸子问答', 'neonopon':'Neo No Pon 方块游戏',
    'popbounc':'Pop Bounce 弹球', 'qad':'问答与龙', 'viewpoin':'视点',
    'ghostlop':'Ghostlop 幽灵方块', 'lbowling':'联盟保龄球',
    'avspirit':'幽灵战士', 'phantasm':'幽灵战士', 'ffightae':'快打旋风 30周年版',
    'gunfront':'炮击前线', 'metalb':'金属黑',
    'pgoal':'得点王 炎之自由球', 'pspikes2':'超级排球 2', 'puzzldpr':'益智方块 R',
    'puzzledp':'益智方块', 'quizdai2':'问答大搜查线 2', 'quizdais':'问答大搜查线',
    'quizkof':'拳皇问答', 'sdodgeb':'超级躲避球', 'socbrawl':'足球乱斗',
    'ssideki':'得点王', 'ssideki2':'得点王 2', 'ssideki3':'得点王 3', 'ssideki4':'得点王 4',
    'stakwin':'赛马赢家', 'stakwin2':'赛马赢家 2', 'tpgolf':'顶尖高尔夫',
    'turfmast':'大赛高尔夫', 'tws96':'得点王 96', 'wjammers':'飞盘大战',
    'cworld2j':'问答世界 2', 'mosyougi':'将棋大师', 'qtono2':'问答殿下 2',
}
ALIASES = {'3wonderu':'3wonders','bngbeadn':'bangbead','burningh':'burningf',
           'captcomj':'captcomm','captcomu':'captcomm','dw':'dynwar','dwj':'dynwar',
           'fightfva':'fightfev','ganryun':'ganryu','garoun':'garou','garouo':'garou',
           'gwingj':'gigawing','kof2004se':'kof2002','kof2k3up':'kof2003',
           'kof2k1nd':'kof2001','kof2k2nd':'kof2002','kof2knd':'kof2000',
           'kof97a':'kof97','kof98n':'kof98','kof99a':'kof99','kof99n':'kof99','kof99nd':'kof99',
           'kov2nd':'kov2','lastblda':'lastblad','mercsua':'mercs','mslug3n':'mslug3',
           'mslug3nd':'mslug3','mslug4nd':'mslug4','ncombata':'ncombat','nitdn':'nitd',
           'pbobblna':'pbobblen','preisl2n':'preisle2','punishrj':'punisher','punishru':'punisher',
           'qadj':'qad','rbff2a':'rbff2','rckman2j':'megaman2','roboarma':'roboarmy',
           'rotdnd':'rotd','s1945pn':'s1945p','samsho3a':'samsho3','samsho5sp':'samsh5sp',
           'sengokh':'sengoku','sf2cej':'sf2ce','sf2m1':'sf2ce','sf2m2':'sf2ce','sf2m3':'sf2ce',
           'sf2m4':'sf2ce','sf2m5':'sf2ce','sf2m6':'sf2ce','sf2m7':'sf2ce','sf2t':'sf2hf',
           'sf2tj':'sf2hf','sf2turyu':'sf2hf','sfz2aa':'sfz2al','sfz2aj':'sfz2al',
           'shocktra':'shocktro','shocktrj':'shocktro','slammasu':'slammast','sngoku3n':'sengoku3',
           'stridrja':'strider','stridrua':'strider','tophunta':'tophuntr','vlinero':'vliner','zupapan':'zupapa',
           'kovhsqj':'kovplus','kovtstd':'kovplus','oldsplus211':'oldsplus','wof3js':'wof',
           'tws96':'twsoc96','mosyougi':'moshougi','qtono2':'qtono2j'}
LEGACY = ['街机全集 待逐款验证', '旧版街机合集 待逐款验证', '飞机精选']


def chinese(text):
    return bool(re.search('[\u4e00-\u9fff]', text))


def base_title(text):
    return re.split(r'[（(]', text)[0].strip()


def family(name, metadata):
    seen = set()
    while name in metadata and metadata[name].get('cloneof') and name not in seen:
        seen.add(name)
        name = metadata[name]['cloneof']
    return name


def category(raw):
    if raw.startswith('Fighter /'):
        return '03-动作闯关' if any(x in raw for x in ('2.5D', 'Field', 'Vertical')) else '04-格斗对战'
    return {'Shooter':'05-飞机与射击', 'Platform':'03-动作闯关', 'Maze':'03-动作闯关',
            'Puzzle':'06-益智休闲', 'Ball & Paddle':'06-益智休闲', 'Driving':'07-赛车与体育',
            'Sports':'07-赛车与体育', 'Tabletop':'08-棋牌与问答', 'Quiz':'08-棋牌与问答',
            'Gambling':'08-棋牌与问答', 'Slot Machine':'08-棋牌与问答'}.get(raw.split(' / ')[0], '09-其他类型')


def safe_label(text):
    return re.sub(r'[&*/:`<>?\\|\"]', '_', text)


def make_item(row, label, playlist):
    return {'path':row['path'], 'label':safe_label(label),
            'core_path':'/usr/lib/libretro/fbneo_libretro.so', 'core_name':'FinalBurn Neo',
            'crc32':'DETECT', 'db_name':playlist+'.lpl'}


def build(library, metadata_file, catver_file, cheat_dir, assets=None):
    metadata = {x.get('name'):dict(x.attrib, description=x.findtext('description',''))
                for x in ET.parse(metadata_file).getroot() if x.get('name')}
    cats = {}; section = ''
    for line in catver_file.read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('['): section=line
        elif section == '[Category]' and '=' in line:
            key,value=line.split('=',1);cats[key]=value
    names = {}
    for p in sorted(library.rglob('*.lst')):
        if p.name not in ('mame.lst','mamecn.lst','lst.lst'): continue
        for line in p.read_text(encoding='utf-8-sig').splitlines():
            fields=line.split('\t')
            if len(fields)>1 and chinese(base_title(fields[1])):
                names[fields[0].lower()]=fields[1].strip()
    pictures = {kind:{p.stem.lower():p for p in library.rglob('*.png') if p.parent.name==kind}
                for kind in ('snap','titles')}
    if assets and assets.exists():
        for kind in ('snap','titles'):
            pictures[kind].update({p.stem.lower():p for p in (assets/kind).glob('*.png')})
    dat_sources=collections.defaultdict(list)
    for p in cheat_dir.glob('*.dat'):
        for name in set(re.findall(r'^:([^:]+):',p.read_bytes().decode('latin1'),re.M)):
            dat_sources[name.lower()].append(str(p))
    files = collections.defaultdict(list)
    for p in sorted(library.rglob('*')):
        if p.suffix.lower()=='.zip' and p.parent.name.lower()=='roms':
            files[p.stem.lower()].append(p)
    rows=[];resources=[]
    for name,paths in files.items():
        meta=metadata.get(name,{})
        if meta.get('isbios')=='yes' or cats.get(name,'').startswith('System /') or name in ('tms32030','tms32031','tms32032','tms32033','211fa_2005-09-23_3434','plugsrc'):
            resources.append(name);continue
        paths.sort(key=lambda p:('MAME 中文典藏版 v4.00' not in str(p),str(p)))
        root=family(name,metadata)
        title=names.get(name) or names.get(root) or OVERRIDES.get(name) or OVERRIDES.get(root)
        alias=ALIASES.get(name)
        if not title and alias:
            title=(names.get(alias) or OVERRIDES.get(alias))
            if title:title=base_title(title)+'（旧合集版本）'
        if not title:
            title=next((v for k,v in names.items() if family(k,metadata)==root),None)
        pending=not bool(title)
        title=title or ('待核中文名 · '+meta.get('description',name))
        snap=pictures['snap'].get(name) or pictures['snap'].get(root) or pictures['snap'].get(alias)
        heading=pictures['titles'].get(name) or pictures['titles'].get(root) or pictures['titles'].get(alias)
        cheat_sources=([str(cheat_dir/(name+'.ini'))] if (cheat_dir/(name+'.ini')).exists() else [])+dat_sources.get(name,[])
        rows.append({'name':name,'family':root,'title':title,'path':str(paths[0]),
                     'other_copies':[str(p) for p in paths[1:]],'supported':name in metadata,
                     'category':category(cats.get(name,cats.get(root,''))),
                     'raw_category':cats.get(name,cats.get(root,'')),
                     'snapshot':str(snap) if snap else None,'title_image':str(heading) if heading else None,
                     'cheat':cheat_sources[0] if cheat_sources else None,'cheat_sources':cheat_sources,
                     'pending_chinese':pending})
    groups=collections.defaultdict(list)
    for row in rows:
        if row['supported']:groups[row['family']].append(row)
    primary=[];variants=[];compat=[]
    for root,group in groups.items():
        group.sort(key=lambda x:(x['name']!=root,'MAME 中文典藏版 v4.00' not in x['path'],x['pending_chinese'],x['name']))
        primary.append(group[0]);variants.extend(group[1:])
    compat=[x for x in rows if not x['supported']]
    lists=collections.defaultdict(list)
    favorites=['dino','wof','mslug','kof97','1941','ddsom'];byname={x['name']:x for x in rows}
    for name in favorites:
        if name in byname:lists['00-飞机精选'].append(byname[name])
    for row in primary:lists[row['category']].append(row)
    lists['01-有金手指的游戏']=[row for row in primary if row['cheat']]
    lists['90-其他地区与修订版本']=variants
    lists['91-兼容性待确认']=compat
    for name,items in lists.items():
        for row in items:
            label=base_title(row['title']) if name not in ('90-其他地区与修订版本','91-兼容性待确认') else row['title']
            row.setdefault('labels',{})[name]=safe_label(label+' ['+row['name']+']')
    return dict(lists),{'rom_files':sum(len(x) for x in files.values()),'unique_shortnames':len(files),
                        'resources_excluded':resources,'preferred_games':len(primary),'variant_games':len(variants),
                        'compatibility_pending':len(compat),'duplicate_copies':sum(len(x)-1 for x in files.values()),
                        'pending_chinese':[x['name'] for x in rows if x['pending_chinese']],
                        'primary_without_snapshots':[x['name'] for x in primary if not x['snapshot']],
                        'primary_without_cheats':[x['name'] for x in primary if not x['cheat']],
                        'lists':{k:len(v) for k,v in lists.items()},'games':rows}


def apply(lists, report, playlist_dir, thumbnails_dir, backup):
    if backup.exists(): raise RuntimeError('Backup must be a new directory')
    backup.mkdir(parents=True)
    if playlist_dir.exists():shutil.copytree(playlist_dir,backup/'playlists')
    cfg=Path.home()/'.config/retroarch/retroarch.cfg';shutil.copy2(cfg,backup/'retroarch.cfg')
    (backup/'catalog-before.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    # Hide only the three old generated lists, not user playlists or ROMs.
    for name in LEGACY:
        p=playlist_dir/(name+'.lpl')
        if p.exists():p.unlink()
    for name,rows in lists.items():
        items=[make_item(row,row['labels'][name],name) for row in rows]
        data={'version':'1.5','default_core_path':'/usr/lib/libretro/fbneo_libretro.so',
              'default_core_name':'FinalBurn Neo','label_display_mode':0,'right_thumbnail_mode':2,
              'left_thumbnail_mode':3,'sort_mode':0,'items':items}
        p=playlist_dir/(name+'.lpl');tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
        for row in rows:
            for kind,key in [('Named_Snaps','snapshot'),('Named_Titles','title_image')]:
                if not row[key]:continue
                dest=thumbnails_dir/name/kind/(row['labels'][name]+'.png');dest.parent.mkdir(parents=True,exist_ok=True)
                if dest.is_symlink() and dest.resolve()==Path(row[key]):continue
                if dest.exists() or dest.is_symlink():
                    saved=backup/'thumbnails'/name/kind/dest.name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved);dest.unlink()
                dest.symlink_to(row[key])
    text=cfg.read_text();settings={'menu_thumbnails':'1','menu_left_thumbnails':'2',
         'materialui_thumbnail_view_landscape':'2','materialui_thumbnail_view_portrait':'1',
         'materialui_dual_thumbnail_list_view_enable':'true','playlist_use_filename':'false',
         'input_overlay_enable':'false','menu_show_online_updater':'false'}
    for key,value in settings.items():
        line=key+' = "'+value+'"'
        text=re.sub(r'^'+re.escape(key)+r'\s*=.*$',lambda _:line,text,flags=re.M) if re.search(r'^'+re.escape(key)+r'\s*=',text,re.M) else text+'\n'+line+'\n'
    cfg.write_text(text)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--library',type=Path,default=Path.home()/'Games/FLIGHT')
    p.add_argument('--metadata',type=Path,required=True);p.add_argument('--catver',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True);p.add_argument('--apply',action='store_true');p.add_argument('--backup',type=Path)
    args=p.parse_args();lists,report=build(args.library,args.metadata,args.catver,Path.home()/'.local/share/retroarch/system/fbneo/cheats',Path.home()/'.local/share/pcadmin-arcade/assets')
    if args.apply:
        if not args.backup:p.error('--apply requires --backup')
        if report['preferred_games']<100:raise RuntimeError('Too few games; refusing to replace catalog')
        apply(lists,report,Path.home()/'.local/share/retroarch/playlists',Path.home()/'.config/retroarch/thumbnails',args.backup)
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='games'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
