"""Prepare the public reading site without changing the local reading edition.

Only docs/ is deployed. Source snapshots, tools, drafts and review logs stay local.
Run with the existing project Python (lxml is required).
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from html import escape
from functools import lru_cache
import json
import os
import posixpath
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit

from lxml import html, etree

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'site' / '_site'
OUTPUT = ROOT / 'docs'
PUBLIC_URL = 'https://musiclord.github.io/music-textbooks-zh/'
POLICY = ROOT / 'publication-policy.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


@lru_cache(maxsize=150000)
def local_target(page, value):
    parts = urlsplit(value)
    if parts.scheme or parts.netloc or not parts.path:
        return None
    parent = page.parent.relative_to(SOURCE).as_posix()
    target = posixpath.normpath(parts.path.lstrip('/') if parts.path.startswith('/')
                               else posixpath.join(parent, unquote(parts.path)))
    if target == '..' or target.startswith('../'):
        raise ValueError(f'Local reference escapes website: {page.name}: {value}')
    return target


def resource_catalog(policy):
    resources = {}
    for filename in ('asset-manifest.json', 'linked-images.json'):
        for item in read(ROOT / 'sources' / filename):
            url = item['url']
            host = urlsplit(url).netloc
            if item['book'] == 'rk' and host == 'www.gutenberg.org':
                basis = 'Historical 1922 edition; Project Gutenberg ebook 33900'
            elif host == 'viva.pressbooks.pub':
                basis = 'OMT CC BY-SA 4.0; individual media credits override the book license'
            elif url.startswith('https://raw.githubusercontent.com/MarkGotham/Anthology/main/OpenScore-LiederCorpus/'):
                basis = 'OpenScore Lieder CC0 transcriptions; OMT harmony anthology attribution retained'
            else:
                basis = None
            resources[item['local']] = {'source': url, 'basis': basis,
                'reason': None if basis else 'Individual redistribution permission not confirmed'}
    for item in read(ROOT / 'sources' / 'score-recoveries.json'):
        url = item['source_url']
        host = urlsplit(url).netloc
        if item['book'] == 'rk' and host == 'www.gutenberg.org':
            basis = 'Pages rendered from the historical Gutenberg 33900 score PDFs'
        elif host == 'viva.pressbooks.pub':
            basis = 'Score supplied with OMT; chapter attribution and exceptions retained'
        else:
            basis = None
        record = {'source': item.get('embed_url') or url, 'basis': basis,
                  'reason': None if basis else 'Individual redistribution permission not confirmed'}
        for page in item.get('pages', []):
            resources[page['local']] = record.copy()
        if item.get('download_local'):
            resources[item['download_local']] = record.copy()
    for path, item in policy['external_only'].items():
        if path not in resources:
            raise ValueError('Policy asset disappeared: ' + path)
        resources[path].update(basis=None, reason=item['reason'])
        if item.get('source'):
            resources[path]['source'] = item['source']
    # New restricted-media notices require a policy update before another release.
    restrictions = {}
    for path in (ROOT / 'manuscripts' / 'omt').glob('*.json'):
        for unit in read(path).get('units', []):
            if 'Media Attributions' in unit.get('en', '') and any(
                marker in unit['en'] for marker in ('All Rights Reserved', 'CC BY-ND', 'CC BY-NC-ND')
            ):
                restrictions[unit['id']] = unit['source_sha256']
    if restrictions != policy['restricted_attribution_units']:
        raise ValueError('Restricted media notices changed; review publication-policy.json first')
    return resources


def external_link(url, label):
    a = etree.Element('a', href=url, target='_blank', rel='noopener noreferrer',
                      attrib={'class': 'external'})
    a.text = label + ' ↗'
    return a


def prepare():
    if not (SOURCE / 'index.html').is_file():
        raise ValueError('Build the local reading edition first')
    if OUTPUT.is_symlink() or OUTPUT.resolve() != ROOT.resolve() / 'docs':
        raise ValueError('Unexpected publication output directory')
    OUTPUT.mkdir(exist_ok=True)
    policy = read(POLICY)
    resources = resource_catalog(policy)
    blocked = {path: data for path, data in resources.items() if not data['basis']}
    used_assets, changed_units, replacements = set(), {}, []
    expected_files = set()
    docs = {}
    print('Preparing public pages and source links...', flush=True)
    for path in sorted(SOURCE.rglob('*.html')):
        relative = path.relative_to(SOURCE).as_posix()
        dom = html.document_fromstring(path.read_text(encoding='utf-8'))
        # A score's unpublished performance directions are also adaptations.
        # Keep the textbook prose, and replace only the score and its directions.
        affected = set()
        for node in list(dom.xpath('//img[@src]')):
            target = local_target(path, node.get('src'))
            if target and target.startswith('assets/') and not target.startswith('assets/katex/'):
                if target not in resources:
                    raise ValueError('Image has no publication provenance: ' + target)
                if target in blocked:
                    unit = next((a for a in node.iterancestors() if 'translation-unit' in a.get('class', '').split()), None)
                    if unit is not None:
                        affected.add(unit)
                    wrap = etree.Element('span', attrib={'class': 'publication-external-media'})
                    if node.get('id'):
                        wrap.set('id', node.get('id'))
                    wrap.append(external_link(blocked[target]['source'], '至原來源查看譜例／圖片'))
                    wrap.tail = node.tail
                    node.getparent().replace(node, wrap)
                    replacements.append({'page': relative, 'asset': target})
        for unit in affected:
            for node in list(unit.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," translated-score-directions ")]')):
                # Preserve any old deep-link anchors while omitting the translation.
                anchor_ids = node.xpath('.//@id') + ([node.get('id')] if node.get('id') else [])
                stub = etree.Element('div')
                for anchor_id in dict.fromkeys(anchor_ids):
                    etree.SubElement(stub, 'span', id=anchor_id)
                node.getparent().replace(node, stub)
            changed_units[unit.get('id')] = unit
        for node in dom.xpath('//*[@href]'):
            target = local_target(path, node.get('href'))
            if target in blocked:
                node.set('href', blocked[target]['source'])
                node.set('target', '_blank')
                node.set('rel', 'noopener noreferrer')
                node.set('class', (node.get('class', '') + ' external').strip())
                node.attrib.pop('download', None)
                if node.text and ('下載' in node.text or 'Download' in node.text):
                    node.text = '至原來源查看 ↗'
        main = dom.xpath('//*[@id="reader-content"]')
        if main:
            note = etree.SubElement(main[0], 'p', attrib={'class': 'publication-note'})
            rel = os.path.relpath(OUTPUT / 'licenses.html', (OUTPUT / relative).parent).replace('\\', '/')
            etree.SubElement(note, 'a', href=rel).text = '來源、授權與版本說明'
            if affected:
                note.text = '本頁部分譜例以原來源連結提供。'
            if relative == 'index.html':
                note.text = '繁中翻譯持續校訂中；部分譜例請至原來源查看。'
        heads = dom.xpath('//head')
        if heads:
            etree.SubElement(heads[0], 'link', rel='canonical', href=PUBLIC_URL + relative)
        for node in dom.xpath('//*[@src or @href]'):
            for attr in ('src', 'href'):
                if node.get(attr):
                    target = local_target(path, node.get(attr))
                    if target and target.startswith('assets/') and not target.startswith('assets/katex/'):
                        if target not in resources:
                            raise ValueError('Asset has no publication provenance: ' + target)
                        if target in blocked:
                            raise ValueError('Blocked asset survived: ' + target)
                        used_assets.add(target)
        docs[relative] = dom

    license_dom = deepcopy(docs['index.html'])
    main = license_dom.xpath('//*[@id="reader-content"]')[0]
    for child in list(main):
        main.remove(child)
    main.append(html.fromstring((ROOT / 'publication-license.html').read_text(encoding='utf-8')))
    license_dom.xpath('//title')[0].text = '來源、授權與版本說明 – 音樂教材'
    license_dom.xpath('//link[@rel="canonical"]')[0].set('href', PUBLIC_URL + 'licenses.html')
    docs['licenses.html'] = license_dom
    print(f'Writing {len(docs)} pages; copying referenced assets...', flush=True)
    for relative, dom in docs.items():
        destination = OUTPUT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(html.tostring(dom, encoding='utf-8', method='html', doctype='<!DOCTYPE html>'))
        expected_files.add(relative)

    # Keep the custom search index, and update entries whose score directions changed.
    index = read(SOURCE / 'search-index.json')
    for item in index:
        key = urlsplit(item['url']).fragment
        if key in changed_units:
            unit = deepcopy(changed_units[key])
            english = unit.xpath('.//details[contains(@class,"english")]')
            item['en'] = ' '.join(e.text_content() for e in english)
            for element in english:
                element.getparent().remove(element)
            item['text'] = ' '.join(unit.text_content().split())
    (OUTPUT / 'search-index.json').write_text(json.dumps(index, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    expected_files.add('search-index.json')

    copies = [SOURCE / 'reader.css', SOURCE / 'reader.js']
    for directory in ('assets/katex', 'site_libs'):
        copies.extend(p for p in (SOURCE / directory).rglob('*') if p.is_file())
    copies.extend(SOURCE / path for path in sorted(used_assets))
    for path in copies:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 25 * 1024 * 1024:
            raise ValueError('Missing, linked or oversized asset: ' + str(path))
        relative = path.relative_to(SOURCE).as_posix()
        destination = OUTPUT / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Avoid copying the unchanged large image collection on every preparation.
        if not destination.exists() or destination.stat().st_size != path.stat().st_size or destination.stat().st_mtime_ns != path.stat().st_mtime_ns:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        expected_files.add(relative)
    with (OUTPUT / 'reader.css').open('a', encoding='utf-8') as stream:
        stream.write('\n.publication-note{font-size:.85rem;color:var(--muted);margin:2rem 0;padding:1rem 0;border-top:1px solid var(--border)}.publication-external-media{display:block;padding:1rem 0}.publication-license{max-width:52rem;margin:auto;padding:2rem 1.5rem;line-height:1.8}\n')
    (OUTPUT / '.nojekyll').write_text('', encoding='utf-8')
    expected_files.add('.nojekyll')
    manifest = {'edition': '2026-09-15', 'site_url': PUBLIC_URL,
                'included_assets': {p: resources[p] for p in sorted(used_assets)},
                'external_only_assets': {p: blocked[p] for p in sorted({r['asset'] for r in replacements})},
                'external_references': replacements}
    (OUTPUT / 'publication-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    expected_files.add('publication-manifest.json')
    # Prune only generated files inside this verified output directory.
    for path in OUTPUT.rglob('*'):
        if path.is_file() and path.relative_to(OUTPUT).as_posix() not in expected_files:
            if path.is_symlink() or not path.resolve().is_relative_to(OUTPUT.resolve()):
                raise ValueError('Unsafe generated file: ' + str(path))
            path.unlink()
    print('Checking public links, search and excluded assets...', flush=True)
    result = verify()
    result['external_only_assets'] = len(manifest['external_only_assets'])
    result['affected_pages'] = len({r['page'] for r in replacements})
    (ROOT / 'reports/publication-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


def verify():
    documents = {p.resolve(): html.parse(str(p)) for p in OUTPUT.rglob('*.html')}
    anchors = {p: set(d.xpath('//@id')) for p, d in documents.items()}
    output_root = OUTPUT.resolve()
    files = [p for p in OUTPUT.rglob('*') if p.is_file()]
    existing = {p.resolve() for p in files}
    manifest = read(OUTPUT / 'publication-manifest.json')
    errors, links, images = [], 0, 0
    for path, dom in documents.items():
        for node in dom.xpath('//*[@href or @src]'):
            for attr in ('href', 'src'):
                value = node.get(attr)
                if not value:
                    continue
                u = urlsplit(value)
                if u.scheme or u.netloc:
                    if u.hostname in ('localhost', '127.0.0.1') or u.scheme == 'file':
                        errors.append('Local URL: ' + value)
                    continue
                if u.path.startswith('/'):
                    errors.append('Root-relative link: ' + value)
                    continue
                target = Path(os.path.abspath(path.parent / unquote(u.path))) if u.path else path
                if target not in existing and target / 'index.html' in existing:
                    target /= 'index.html'
                links += 1
                images += node.tag == 'img' and attr == 'src'
                if not target.is_relative_to(output_root) or target not in existing:
                    errors.append(path.name + ': missing ' + value)
                elif target.suffix == '.html' and u.fragment and unquote(u.fragment) not in anchors.get(target, set()):
                    errors.append(path.name + ': missing anchor ' + value)
        ids = dom.xpath('//@id')
        if len(ids) != len(set(ids)):
            errors.append('Duplicate IDs: ' + path.name)
    for path in manifest['external_only_assets']:
        if (OUTPUT / path).exists():
            errors.append('External-only asset was copied: ' + path)
    for item in read(OUTPUT / 'search-index.json'):
        u = urlsplit(item['url'])
        target = Path(os.path.abspath(OUTPUT / unquote(u.path).lstrip('/')))
        if target not in anchors or unquote(u.fragment) not in anchors[target]:
            errors.append('Invalid search result: ' + item['url'])
    for path in OUTPUT.rglob('*'):
        if path.is_file() and path.suffix.lower() in {'.html', '.json', '.js', '.css', '.md'}:
            text = path.read_text(encoding='utf-8')
            if re.search(r'C:[\\/]Users[\\/]|(?:ghp_|github_pat_)[A-Za-z0-9_]{20,}|-----BEGIN .*PRIVATE KEY-----', text):
                errors.append('Private data marker: ' + path.name)
    result = {'html_pages': len(documents), 'checked_local_links': links,
              'image_references': images, 'files': len(files),
              'bytes': sum(p.stat().st_size for p in files), 'errors': errors}
    if errors:
        raise ValueError(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(), ensure_ascii=False))
    else:
        prepare()
