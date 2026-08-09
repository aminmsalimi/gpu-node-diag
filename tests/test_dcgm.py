from gpunodediag.checks.dcgm import (
    check_dcgm_results,
    check_dcgm_status,
)
from gpunodediag.collectors.dcgm import (
    parse_dcgm_diag_json,
)
from gpunodediag.models import (
    DCGMStatus,
    DCGMTestResult,
    Severity,
)


SAMPLE_JSON = r"""
{
  "category": "Integration",
  "tests": [
    {
      "name": "pcie",
      "results": [
        {
          "entity_group": "GPU",
          "entity_group_id": 1,
          "entity_id": 0,
          "info": [
            "GPU to Host bandwidth: 42 GB/s"
          ],
          "status": "Pass"
        },
        {
          "entity_group": "GPU",
          "entity_group_id": 1,
          "entity_id": 1,
          "warnings": [
            "PCIe throughput below threshold"
          ],
          "status": "Fail"
        }
      ],
      "test_summary": {
        "status": "Fail"
      }
    }
  ]
}
"""


def test_dcgm_json_parser():
    results = parse_dcgm_diag_json(
        SAMPLE_JSON
    )

    assert len(results) == 2

    assert results[0].name == "pcie"
    assert results[0].status == "Pass"
    assert results[0].entity_id == 0

    assert results[1].status == "Fail"
    assert results[1].entity_id == 1


def test_dcgm_failure_becomes_high_finding():
    results = [
        DCGMTestResult(
            name="memory",
            status="Fail",
            entity_group="GPU",
            entity_id=2,
        )
    ]

    findings = check_dcgm_results(
        results
    )

    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert findings[0].code == "DCGM_MEMORY"


def test_dcgm_warning_becomes_warning():
    results = [
        DCGMTestResult(
            name="pcie",
            status="Warning",
            entity_group="GPU",
            entity_id=0,
        )
    ]

    findings = check_dcgm_results(
        results
    )

    assert findings[0].severity is Severity.WARNING


def test_dcgm_pass_is_not_a_finding():
    results = [
        DCGMTestResult(
            name="software",
            status="Pass",
        )
    ]

    assert check_dcgm_results(
        results
    ) == []


def test_missing_dcgm_is_not_failure_in_normal_scan():
    status = DCGMStatus(
        installed=False,
    )

    assert check_dcgm_status(
        status,
        deep_requested=False,
    ) == []


def test_missing_dcgm_is_warning_for_deep_scan():
    status = DCGMStatus(
        installed=False,
    )

    findings = check_dcgm_status(
        status,
        deep_requested=True,
    )

    assert len(findings) == 1
    assert (
        findings[0].code
        == "DCGM_NOT_INSTALLED"
    )


def test_unreachable_hostengine_is_warning():
    status = DCGMStatus(
        installed=True,
        hostengine_reachable=False,
        error="connection refused",
    )

    findings = check_dcgm_status(
        status
    )

    assert len(findings) == 1
    assert (
        findings[0].code
        == "DCGM_HOSTENGINE_UNREACHABLE"
    )