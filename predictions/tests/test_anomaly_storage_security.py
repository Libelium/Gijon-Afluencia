"""
Regression tests for SEC-019 - arbitrary code execution through the anomaly bundle.

`pickle.load` is an interpreter, not a parser, so write access to
`anomalies_detection/{tenant}/{scope}/models/` used to be remote code execution in
the prediction worker. The finding is a reappearance (SEC-001 of the first
delivery), so it gets tests this time.

Two layers are checked here, because they fail independently:
  * the HMAC keeps a bundle this deployment did not write out of the unpickler;
  * the restricted unpickler holds even when the signature is valid, which is the
    layer that matters if the key itself ever leaks.
"""

import hashlib
import hmac
import io
import os
import pickle
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from crowd_predictions.anomaly_detection import core, storage
from crowd_predictions.anomaly_detection.storage import (DisallowedBundleClassError,
                                                         UnsignedBundleError)

KEY = "unit-test-hmac-key"


@pytest.fixture(autouse=True)
def _hmac_key(monkeypatch):
    monkeypatch.setenv("ANOMALY_STATE_HMAC_KEY", KEY)


@pytest.fixture
def profile() -> core.DatamodelProfile:
    return core.DatamodelProfile(
        datamodel="Probe", measure_names=["a", "b"], cadence_minutes=60,
        calendar_cycles=["hour"], decay_window=100, rolling_window=10,
        regime_shift_points=5,
    )


@pytest.fixture
def fitted_state(profile) -> core.DatamodelAnomalyState:
    """A realistic bundle: Birch actually fitted, so the CF-tree exists."""
    state = core.DatamodelAnomalyState.new(profile)
    state.birch.partial_fit(np.random.rand(50, len(profile.feature_columns)))
    window = state.window_for("urn:ngsi-ld:Probe:1", profile)
    for measure in window:
        window[measure].extend([1.0, 2.0, 3.0])
    # A tz-aware datetime, which is what core.evaluate_batch stores
    # (`state.watermarks[entity_id] = point["timestamp"]`). It also makes this
    # fixture exercise the datetime/timezone/timedelta entries of the allow
    # list, which a float watermark would not.
    state.watermarks["urn:ngsi-ld:Probe:1"] = datetime(
        2024, 1, 1, 6, 30, tzinfo=timezone(timedelta(hours=2))
    )
    return state


class _Rce:
    """A payload of the shape a real attacker would store."""

    def __reduce__(self):
        return (os.system, ("true",))


def _sign_with(key: bytes, payload: bytes) -> bytes:
    return storage._BUNDLE_MAGIC + hmac.new(key, payload, hashlib.sha256).digest() + payload


# --------------------------------------------------------------------------- #
# The bundle must still work - a security fix that breaks the vertical is no fix
# --------------------------------------------------------------------------- #
class TestRoundTrip:
    def test_state_survives_a_round_trip(self, fitted_state, tmp_path):
        path = str(tmp_path / "bundle.pkl")
        storage._pickle_save(fitted_state, path)
        back = storage._pickle_load(path)

        assert isinstance(back, core.DatamodelAnomalyState)
        assert back.watermarks == fitted_state.watermarks
        np.testing.assert_allclose(
            back.birch.subcluster_centers_, fitted_state.birch.subcluster_centers_
        )

    def test_incremental_learning_still_works_after_a_reload(self, fitted_state,
                                                             profile, tmp_path):
        """
        The reason the bundle stays a pickle: `partial_fit` needs Birch's private
        CF-tree, which has no public accessor to serialise to JSON. If this ever
        stops holding, a JSON bundle becomes viable and the pickle can go.
        """
        path = str(tmp_path / "bundle.pkl")
        storage._pickle_save(fitted_state, path)
        back = storage._pickle_load(path)

        back.birch.partial_fit(np.random.rand(5, len(profile.feature_columns)))
        assert len(back.birch.subcluster_centers_) >= 1

    def test_the_stored_file_is_framed_and_signed(self, fitted_state, tmp_path):
        path = str(tmp_path / "bundle.pkl")
        storage._pickle_save(fitted_state, path)
        blob = (tmp_path / "bundle.pkl").read_bytes()

        assert blob.startswith(storage._BUNDLE_MAGIC)
        payload = blob[len(storage._BUNDLE_MAGIC) + storage._HMAC_SIZE:]
        expected = hmac.new(KEY.encode(), payload, hashlib.sha256).digest()
        assert blob[len(storage._BUNDLE_MAGIC):][:storage._HMAC_SIZE] == expected


# --------------------------------------------------------------------------- #
# Layer 1 - integrity
# --------------------------------------------------------------------------- #
class TestSignatureIsRequired:
    def test_a_bare_pickle_is_refused(self, fitted_state, tmp_path):
        """Also covers every bundle written before this change: unsigned."""
        path = tmp_path / "legacy.pkl"
        path.write_bytes(pickle.dumps(fitted_state))
        with pytest.raises(UnsignedBundleError):
            storage._pickle_load(str(path))

    def test_a_bundle_signed_with_another_key_is_refused(self, fitted_state, tmp_path):
        payload = pickle.dumps(fitted_state)
        path = tmp_path / "foreign.pkl"
        path.write_bytes(_sign_with(b"someone-elses-key", payload))
        with pytest.raises(UnsignedBundleError):
            storage._pickle_load(str(path))

    def test_a_tampered_payload_is_refused(self, fitted_state, tmp_path):
        path = tmp_path / "bundle.pkl"
        storage._pickle_save(fitted_state, str(path))
        blob = bytearray(path.read_bytes())
        blob[-1] ^= 0xFF                      # flip a bit in the payload
        path.write_bytes(bytes(blob))
        with pytest.raises(UnsignedBundleError):
            storage._pickle_load(str(path))

    def test_truncated_file_is_refused(self, tmp_path):
        path = tmp_path / "short.pkl"
        path.write_bytes(b"PID")
        with pytest.raises(UnsignedBundleError):
            storage._pickle_load(str(path))

    def test_an_unconfigured_key_refuses_rather_than_loads(self, fitted_state,
                                                           tmp_path, monkeypatch):
        """Fail-closed: no key must never mean "accept anything"."""
        path = tmp_path / "bundle.pkl"
        storage._pickle_save(fitted_state, str(path))
        monkeypatch.setenv("ANOMALY_STATE_HMAC_KEY", "")
        with pytest.raises(UnsignedBundleError):
            storage._pickle_load(str(path))


# --------------------------------------------------------------------------- #
# Layer 2 - the restricted unpickler, i.e. what holds if the key leaks
# --------------------------------------------------------------------------- #
class TestRestrictedUnpickler:
    def test_a_correctly_signed_rce_payload_is_still_refused(self, tmp_path):
        payload = pickle.dumps(_Rce())
        path = tmp_path / "signed_evil.pkl"
        path.write_bytes(_sign_with(KEY.encode(), payload))

        with pytest.raises(DisallowedBundleClassError) as excinfo:
            storage._pickle_load(str(path))
        assert "system" in str(excinfo.value)

    def test_the_payload_does_not_run_while_being_refused(self, tmp_path):
        """The class must be refused at find_class, before __reduce__ is called."""
        marker = tmp_path / "executed"

        class Marker:
            def __reduce__(self):
                return (os.system, (f"touch {marker}",))

        payload = pickle.dumps(Marker())
        path = tmp_path / "signed_marker.pkl"
        path.write_bytes(_sign_with(KEY.encode(), payload))

        with pytest.raises(DisallowedBundleClassError):
            storage._pickle_load(str(path))
        assert not marker.exists()

    def test_an_object_dtype_numpy_array_cannot_smuggle_a_gadget(self, tmp_path):
        """
        `numpy._core.multiarray.scalar` is on the allow list because real bundles
        need it, so check it is not a way back in: an object-dtype array's
        contents are resolved by the SAME restricted unpickler, not a fresh one.
        """
        payload = pickle.dumps(np.array([_Rce()], dtype=object))
        path = tmp_path / "numpy_evil.pkl"
        path.write_bytes(_sign_with(KEY.encode(), payload))

        with pytest.raises(DisallowedBundleClassError):
            storage._pickle_load(str(path))

    @pytest.mark.parametrize(
        "module, name",
        [
            ("builtins", "eval"),
            ("builtins", "exec"),
            ("os", "system"),
            ("subprocess", "Popen"),
            ("posix", "system"),
        ],
    )
    def test_known_gadgets_are_not_resolvable(self, module, name):
        unpickler = storage._RestrictedUnpickler(io.BytesIO(b""))
        with pytest.raises(DisallowedBundleClassError):
            unpickler.find_class(module, name)

    def test_the_allow_list_covers_exactly_what_a_real_bundle_needs(
        self, fitted_state, tmp_path
    ):
        """
        Records every find_class a real, fitted bundle makes and asserts the allow
        list covers it. This is what stops the list being widened by guesswork the
        next time numpy or sklearn reorganises a module: the test names the gap.
        """
        path = tmp_path / "bundle.pkl"
        storage._pickle_save(fitted_state, str(path))
        blob = path.read_bytes()
        payload = blob[len(storage._BUNDLE_MAGIC) + storage._HMAC_SIZE:]

        seen = set()

        class Recorder(pickle.Unpickler):
            def find_class(self, module, name):
                seen.add((module, name))
                return super().find_class(module, name)

        Recorder(io.BytesIO(payload)).load()

        missing = seen - storage._ALLOWED_CLASSES
        assert not missing, f"a real bundle needs classes that are not allowed: {missing}"
