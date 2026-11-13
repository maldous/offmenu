from pathlib import Path
root=Path(__file__).resolve().parent
incident=(root/'windmill_incidents.py').read_text()
transport=(root/'ssh_transport.py').read_text()
header='#requirements:\n#paramiko==5.1.0\n#wmill==1.850.0\n'
(root/'windmill_platform_check.py').write_text(header+incident+'\n\n'+transport+'\n\n'+(root/'platform_check_entrypoint.py').read_text())
probe='''\n\ndef main(operation: str = "positive", logical_job_id: str = "native-selftest-20261027"):
    if operation not in ("positive", "negative", "duplicate"):
        raise ValueError("SELFTEST_OPERATION_INVALID")
    if operation == "positive":
        return {"ok": True, "test": True, "incident_recorded": False}
    receipt = record_incident(logical_job_id, "selftest", "SELFTEST_FAILURE",
                              "u/admin/offmenu_incident_selftest", test=True)
    if operation == "negative":
        raise RuntimeError("SELFTEST_FAILURE_INCIDENT_RECORDED")
    return receipt
'''
(root/'incident_selftest.py').write_text('#requirements:\n#wmill==1.850.0\n'+incident+probe)
