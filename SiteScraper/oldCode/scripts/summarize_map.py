import json
p='data/link_file_status_map.json'
js=json.load(open(p))
maps=js['mappings']
total=len(maps)
success=sum(1 for m in maps if m['status']=='successful')
failed=total-success
missing_files=sum(1 for m in maps if not m['filenames'])
print(f"total mappings: {total}")
print(f"successful: {success}")
print(f"failed: {failed}")
print(f"mappings with missing filename: {missing_files}")
print('\nexample failed entries:')
for s in [m for m in maps if m['status']=='failed'][:6]:
    print('-', s['link'], '=>', s['filenames'] or '<no-file>', s['system'], s.get('status_abbreviation'), s.get('status_code'))
print('\nexample missing-file entries:')
for s in [m for m in maps if not m['filenames']][:6]:
    print('-', s['link'], '=>', s['system'], s.get('status_abbreviation'), s.get('status_code'))

# count duplicate files
file_to_links = {}
for r in maps:
    for f in (r['filenames'] or '').split(';'):
        if not f: continue
        file_to_links.setdefault(f, set()).add(r['link'])
dups = {f:len(links) for f,links in file_to_links.items() if len(links)>1}
print('\nduplicate files (count):', len(dups))
print('\nexample duplicate file usages:')
for f, n in list(dups.items())[:8]:
    print('-', f, 'mapped to', n, 'links')
