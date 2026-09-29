"""Floor/address inputs must not erase known contradictions."""
import pytest
from scraper import identity, gratka, morizon, otodom, normalize, rcn


@pytest.mark.parametrize('value,expected', [
    ('GROUND', 0), ('FIRST', 1), ('SECOND', 2), ('TENTH', 10),
    ('parter', 0), ('suterena', -1), ('3', 3), (3.0, 3),
    ('floor_0', 0), ('floor_3', 3), ('floor_11', 11), ('floor_-1', -1),
    ('floor_10+', None),
    ('> 10', None), ('OVER_TENTH', None), ('GARRET', None), ('UNKNOWN', None),
    (None, None), (True, None), (1.5, None),
])
def test_floor_interpretation_is_shared(value, expected):
    assert identity.known_floor(value) == rcn._floor_int(value) == expected


def test_otodom_keeps_unknown_floor_and_normalizes_known_enums():
    items = [{'id':i,'slug':str(i),'estate':'FLAT','floorNumber':v}
             for i,v in enumerate(['FIRST','GROUND','OVER_TENTH'])]
    assert [r['floor'] for r in otodom.parse_items(items,'flat')] == [1,0,'OVER_TENTH']


@pytest.mark.parametrize('module',[gratka,morizon])
def test_county_breadcrumb_is_not_a_town(module):
    assert module._locality('Polna, Czeladź, będziński, śląskie') == 'Czeladź'
    assert module._district('Polna, Czeladź, będziński, śląskie') == 'Polna'
    assert module._locality('Wisła, cieszyński, śląskie') == 'Wisła'
    assert module._locality('Brzeg, powiat brzeski, opolskie') == 'Brzeg'
    assert module._locality('będziński, śląskie') is None
    assert module._locality('Żarki-Letnisko, śląskie') == 'Żarki-Letnisko'
    assert module._locality('Tarnów Opolski, opolskie') == 'Tarnów Opolski'
    assert module._locality('Nieznana nazwa, śląskie') == 'Nieznana nazwa'


@pytest.mark.parametrize('a,b,compatible', [
    ('Zygmuntowska 3a','Zygmuntowska',True),
    ('Zygmuntowska 3 A','ul. Zygmuntowska 3a',True),
    ('Zygmuntowska 3a','Zygmuntowska 3b',False),
    ('11 Listopada 3a','11 Listopada',True),
    ('11 Listopada','3 Listopada',False),
    ('Powstańców 1863','Powstańców 1944',False),
    ('Dywizjonu 303','Dywizjonu 302',False),
])
def test_street_number_variants_preserve_genuine_differences(a,b,compatible):
    assert identity.compatible({'type':'flat','street':a}, {'type':'flat','street':b}) is compatible


def test_photo_variants_join_and_enum_floor_conflicts_stay_separate():
    base={'type':'flat','area':50,'rooms':2,'locality':'Gliwice','source':'otodom',
          'price':400000,'phashes':[3],'floor':'FIRST','street':'Zygmuntowska 3a'}
    a=dict(base,url='a');b=dict(base,url='b',floor=1,street='Zygmuntowska')
    assert len(normalize.dedupe([a,b]))==1
    assert len(normalize.dedupe([a,dict(b,floor='SECOND')]))==2
    assert len(normalize.dedupe([a,dict(b,street='Zygmuntowska 3b')]))==2


def test_rcn_rejects_known_enum_floor_and_building_conflicts():
    rec={'type':'flat','area':50,'first_seen':'2026-06-01',
         'snapshot':{'locality':'Gliwice','rooms':2,'floor':'FIRST','street':'Polna 3a'}}
    tx={'d':'2021-01-01','c':400000,'a':50,'msc':'Gliwice','ul':'Polna','nr':'3a',
        'izb':2,'kond':7,'rynek':'w'}
    assert rcn.match([rec],{'lokale':[tx],'budynki':[]},log=lambda *a:None)==0
    assert rcn.match([rec],{'lokale':[dict(tx,kond=2)],'budynki':[]},log=lambda *a:None)==1
    assert rcn.match([rec],{'lokale':[dict(tx,kond=2,nr='3b')],'budynki':[]},log=lambda *a:None)==0


def test_bit_distance_preserves_old_distance_for_full_hash_width():
    import random
    rng=random.Random(41)
    for _ in range(1000):
        a,b=rng.getrandbits(256),rng.getrandbits(256)
        assert normalize._hamming(a,b)==bin(a^b).count('1')


def test_building_separators_are_not_erased():
    assert identity.street_parts('. 13') == ('. 13', None)
    assert not identity.compatible({'street':'Polna 13/2'}, {'street':'Polna 132'})
    assert identity.compatible({'street':'Polna 13 A'}, {'street':'Polna', 'nr':'13a'})
    rec = {'area':50}
    snap = {'street':'Polna 13/2'}
    assert rcn._score(rec, snap, {'ul':'Polna 132','a':50}, True) == (0, False)
    assert rcn._score(rec, snap, {'ul':'Polna 13/2','a':50}, True) == (2, True)
