from zog.image_build.runtime_composition import select
from zog.image_build.metadata import Package, order
from zog.image_build import host_labels
from zog.image_build.filesystem import inventory


def package(name, build=(), runtime=()):
    return Package(name, (), build, runtime, {}, {}, (), {})


def test_refresh_removes_obsolete_files_and_preserves_old_root(tmp_path):
    def record(name, files):
        root = tmp_path/name
        root.mkdir()
        for path, text in files.items():
            target = root/path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        return dict(identity=name, root=str(root), outputs=inventory(root),
                    provenance={'output': name+'-output', 'result': name+'-result'})
    old = record('old', {'usr/obsolete': 'old', 'usr/current': 'old'})
    new = record('new', {'usr/current': 'new'})
    base = record('base', {'usr/retained': 'base'})
    fixture = record('fixture', {'etc/test-only': 'fixture'})
    before = inventory(old['root'])
    definitions = {'app': package('app', build=('fixture',), runtime=('base',)),
                   'fixture': package('fixture')}
    defs, targets, built = select(definitions, ['app'], ['app', 'base'],
                                  {'app': new, 'base': base, 'fixture': fixture})
    assert defs['app'] is definitions['app']
    assert set(built) == {'app', 'base'}
    assert built['app']['provenance'] == new['provenance']
    attempt = tmp_path/'assembly'
    attempt.mkdir()
    root = host_labels.compose(attempt, built, order(defs, targets, runtime_only=True),
                               host_labels.snapshot(built))
    assert (root/'usr/current').read_text() == 'new'
    assert (root/'usr/retained').read_text() == 'base'
    assert not (root/'usr/obsolete').exists()
    assert not (root/'etc/test-only').exists()
    assert inventory(old['root']) == before


def test_multiple_replacements_preserve_runtime_edges_without_cycles():
    definitions = {'a': package('a', runtime=('b',)), 'b': package('b')}
    defs, targets, built = select(definitions, ['a', 'b'], ['a', 'b', 'c'],
                                  {'a': 1, 'b': 2, 'c': 3})
    assert order(defs, targets, runtime_only=True) == ('b', 'a', 'c')
    assert built == {'a': 1, 'b': 2, 'c': 3}
