from app.utils.process_tracker import node_label, track


def test_node_label_maps_known_nodes():
    assert node_label("sub_feature_generate") == "Generating sub-features"


def test_track_uses_caller_module_name(caplog):
    import logging

    caplog.set_level(logging.INFO)
    track("generate sub-features", feature_id=17)
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.name == __name__
    assert record.message == "generate sub-features (feature_id=17)"
