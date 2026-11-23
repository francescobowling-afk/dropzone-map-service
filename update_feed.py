#!/usr/bin/env python3
"""Dropzone Guide: catalogo mappa, missioni e schede verificate.

Non inventa NPC, luoghi o coordinate. Un feed NPC esterno è facoltativo:
variabile d'ambiente DROPZONE_NPC_FEED_URL (HTTPS, JSON con items[]).
"""
import datetime
import json
import os
import pathlib
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent
OUT = BASE / 'mappa-verificata.json'
INPUT = BASE / 'data' / 'verified-points.json'
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()
URLS = {
    'map': 'https://fortnite-api.com/v1/map',
    'quests': 'https://prod.fn-api.cc/v1/quests?lang=it',
}
BLOCK = ('fortnite.gg', 'fortnite.gs', 'fortnite database')
KINDS = ('Location', 'NPC', 'Luoghi nascosti', 'Obiettivi')


def text(value, limit=450):
    return str(value).strip()[:limit] if isinstance(value, (str, int, float)) else ''


def entries(value):
    return value if isinstance(value, list) else list(value.values()) if isinstance(value, dict) else []


def get_json(url):
    if not isinstance(url, str) or not url.startswith('https://') or any(x in url.lower() for x in BLOCK):
        raise ValueError('URL non autorizzato')
    request = urllib.request.Request(url, headers={'User-Agent': 'DropzoneGuide/1.4', 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def coords(entry):
    value = entry.get('normalizedPosition') or entry.get('normalizedCoordinates') or entry.get('mapPosition') or entry
    if not isinstance(value, dict):
        return {}
    x, y = value.get('x'), value.get('y')
    if type(x) in (int, float) and type(y) in (int, float) and 0 <= x <= 1 and 0 <= y <= 1:
        return {'x': x, 'y': y}
    return {}


def parse_map(payload):
    root = payload.get('data', payload)
    return [{
        'id': 'poi:' + text(p.get('id') or p.get('name'), 110),
        'kind': 'Location', 'name': text(p.get('name'), 110),
        'description': 'Punto di interesse riportato da Fortnite-API',
        'source': 'Fortnite-API', 'sourceUrl': URLS['map'], **coords(p),
    } for p in entries(root.get('pois')) if isinstance(p, dict) and text(p.get('name'))][:350]


def quest_objectives(quest):
    result = []
    for obj in entries(quest.get('objectives'))[:30]:
        if not isinstance(obj, dict):
            continue
        label = text(obj.get('description') or obj.get('text') or obj.get('name') or obj.get('title'), 220)
        if label and label not in result:
            result.append(label)
    return result


def parse_quests(payload):
    root = payload.get('data', payload)
    pool = next((root.get(k) for k in ('quests', 'athenaQuests', 'brQuests', 'questDefinitions', 'questMap')
                 if isinstance(root, dict) and isinstance(root.get(k), (list, dict))), None)
    if pool is None and isinstance(root, list):
        pool = root
    result = []
    for index, quest in enumerate(entries(pool)):
        if not isinstance(quest, dict):
            continue
        name = text(quest.get('name') or quest.get('title') or quest.get('displayName') or quest.get('questName'), 110)
        if not name:
            continue
        objectives = quest_objectives(quest)
        description = text(quest.get('description') or quest.get('shortDescription')) or (objectives[0] if objectives else 'Consulta la missione nel gioco')
        # searchHint permette la ricerca per azione senza attribuire coordinate arbitrarie.
        result.append({
            'id': 'quest:' + text(quest.get('templateId') or quest.get('id') or index, 100),
            'kind': 'Obiettivi', 'name': name, 'description': description,
            'searchHint': ' · '.join(objectives)[:600],
            'source': 'FN Api', 'sourceUrl': URLS['quests'],
        })
    return result[:1200]


def parse_verified(payload, default_source='Fonte verificata'):
    if not isinstance(payload, dict) or not isinstance(payload.get('items'), list):
        raise ValueError('Il feed deve contenere items[]')
    result = []
    for item in payload['items'][:2500]:
        if not isinstance(item, dict) or item.get('kind') not in KINDS or not text(item.get('name')):
            continue
        url = text(item.get('sourceUrl'), 500)
        if not url.startswith('https://') or any(block in url.lower() for block in BLOCK):
            continue
        point = coords(item)
        zone = text(item.get('zoneName'), 110)
        result.append({
            'id': text(item.get('id') or item['name'], 110),
            'kind': item['kind'], 'name': text(item['name'], 110),
            'description': text(item.get('description')) or 'Informazione riportata dalla fonte',
            'zoneName': zone, 'searchHint': text(item.get('searchHint'), 600),
            'accuracy': 'precise' if point else ('approximate' if zone else 'unknown'),
            'source': text(item.get('source')) or default_source,
            'sourceUrl': url, **point,
        })
    return result


def load_curated():
    if not INPUT.exists():
        return []
    return parse_verified(json.loads(INPUT.read_text(encoding='utf-8')), 'Verifica manuale')


def main():
    try:
        old = json.loads(OUT.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        old = {'items': [], 'sourceStatus': {}}
    previous = entries(old.get('items'))
    fresh = []
    statuses = {}
    any_success = False
    jobs = [('map', URLS['map'], parse_map, 'Fortnite-API'),
            ('quests', URLS['quests'], parse_quests, 'FN Api')]
    npc_url = os.environ.get('DROPZONE_NPC_FEED_URL', '').strip()
    if npc_url:
        jobs.append(('npc', npc_url, lambda data: [p for p in parse_verified(data, 'Feed NPC') if p['kind'] == 'NPC'], 'Feed NPC'))
    else:
        statuses['npc'] = {'ok': False, 'checkedAt': NOW, 'error': 'Nessuna fonte NPC verificata configurata'}

    for name, url, parser, source in jobs:
        try:
            data = parser(get_json(url))
            if not data:
                raise ValueError('Nessun elemento valido ricevuto')
            fresh.extend(data)
            statuses[name] = {'ok': True, 'checkedAt': NOW, 'count': len(data)}
            any_success = True
        except Exception as error:
            statuses[name] = {'ok': False, 'checkedAt': NOW, 'error': str(error)[:120]}
            fresh.extend(item for item in previous if item.get('source') == source)

    try:
        curated = load_curated()
        fresh.extend(curated)
        statuses['curated'] = {'ok': True, 'checkedAt': NOW, 'count': len(curated)}
    except Exception as error:
        statuses['curated'] = {'ok': False, 'checkedAt': NOW, 'error': str(error)[:120]}
        fresh.extend(item for item in previous if item.get('source') not in ('Fortnite-API', 'FN Api', 'Feed NPC'))

    unique = {}
    for item in fresh:
        if isinstance(item, dict) and item.get('name') and item.get('kind') in KINDS:
            unique[(item['kind'], item.get('id') or item['name'])] = item
    items = list(unique.values()) or previous
    output = {
        'schemaVersion': 3, 'generatedAt': NOW,
        'lastSuccessfulDataAt': NOW if any_success else old.get('lastSuccessfulDataAt'),
        'sourceStatus': statuses, 'items': items,
        'status': 'Coordinate solo se verificate; NPC da fonte configurata o catalogo manuale',
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Pubblicati', len(items), 'elementi')
    print('Categorie:', {kind: sum(item.get('kind') == kind for item in items) for kind in KINDS})


if __name__ == '__main__':
    main()
