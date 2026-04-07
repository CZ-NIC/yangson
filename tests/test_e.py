import pytest
from yangson import DataModel
from yangson.schemadata import IdentityAdjacency

"""
Test description

Test all features versus only implemented features from the YANG Library.
Test behaviour of import only modules: All identities are available.
"""

# TODO checks that all YANG Library features are defined in the modules

@pytest.fixture
def schema_data():
    data_model = DataModel.from_file("yang-modules/teste/yang-library.json",
                                     ["yang-modules/teste", "yang-modules/ietf"])

    return data_model.schema_data

def test_impl_features(schema_data):
    # implemeneted features are always stored on main modules, never on submodules
    assert schema_data.modules[("test-main", "2026-04-01")].features == \
            set(("feature-m-b", "feature-s-a"))
    assert schema_data.modules[("test-import-complex", "2026-04-01")].features == \
            set(("sub-a", "sub-a-a", "sub-b-b"))
    assert schema_data.modules[("main-sub-a", "2026-04-01")].features == set()
    assert schema_data.modules[("impo-sub-b", "")].features == set()
    assert schema_data.modules[("ietf-yang-types", "2025-12-22")].features == set()
    assert schema_data.modules[("ietf-inet-types", "2013-07-15")].features == set()


def test_all_features(schema_data):
    # Per module defined features
    assert schema_data.modules[("test-main", "2026-04-01")].all_features == \
            set(("feature-m-a", "feature-m-b"))
    assert schema_data.modules[("main-sub-a", "2026-04-01")].all_features == \
            set(("feature-s-a",))
    # Note the module 'test-import-only' is not 'implement' module but 'import'
    assert schema_data.modules[("test-main", "2026-04-01")].all_features == \
            set(("feature-m-a", "feature-m-b"))
    assert schema_data.modules[("impo-sub-b", "")].all_features == \
            set(("sub-b-a", "sub-b-b"))
    assert schema_data.modules[("ietf-yang-types", "2025-12-22")].all_features == set()
    assert schema_data.modules[("ietf-inet-types", "2013-07-15")].all_features == set()

    # all features of a module with it's submodules
    assert schema_data.modules[("test-main", "2026-04-01")].get_all_features(schema_data) == \
            set(("feature-m-a", "feature-m-b", "feature-s-a", "feature-s-b"))
    assert schema_data.modules[("test-import-complex", "2026-04-01")].get_all_features(schema_data) == \
            set(("sub-a", "sub-b", "sub-a-a", "sub-a-b", "sub-b-a", "sub-b-b"))

def test_identity_adjacency():
    v1 = IdentityAdjacency()
    assert v1 == v1
    v2 = IdentityAdjacency()
    assert v1 == v2
    v3 = IdentityAdjacency()
    v3.derivs.add(('example', 'test-main'))
    assert v1 != v3

def test_import_identities(schema_data):
    ident_base = IdentityAdjacency()
    ident_base.derivs.add(('ident-m-a', 'test-main'))
    ident_base.derivs.add(('ident-sub-deriv', 'test-main'))
    ident_m_a = IdentityAdjacency()
    ident_m_a.bases.add(('ident-base', 'test-main'))
    ident_sub_deriv = IdentityAdjacency()
    ident_sub_deriv.bases.add(('ident-base', 'test-main'))

    import_id  = IdentityAdjacency()
    import_id.derivs.add(('import-deriv-id', 'test-import-complex'))
    import_deriv_id = IdentityAdjacency()
    import_deriv_id.bases.add(('import-id', 'test-import-complex'))
    assert schema_data.identity_adjs == {
            ('ident-base', 'test-main'): ident_base,
            ('ident-m-a', 'test-main'): ident_m_a,
            ('ident-s-a', 'test-main'): IdentityAdjacency(),
            ('ident-sub-deriv', 'test-main'): ident_sub_deriv,
            # don't forget to import only identities
            ('import-id', 'test-import-complex'): import_id,
            ('import-deriv-id', 'test-import-complex'): import_deriv_id,
            ('impo-sub-a', 'test-import-complex'): IdentityAdjacency(),
            ('impo-sub-b', 'test-import-complex'): IdentityAdjacency(),
            }

