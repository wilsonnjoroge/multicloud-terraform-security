
============================================================================================================================

The default directory for keeping the inventory checks eg 

    AWS Resource Explorer

        1. SH
            ./aws-inventory-check.sh > resource-explorer/before-apply-$(date +%d%m%Y%H%M).txt
            ./aws-inventory-check.sh > resource-explorer/after-apply-$(date +%d%m%Y%H%M).txt

            ./aws-inventory-check.sh > resource-explorer/before-destroy-$(date +%d%m%Y%H%M).txt
            ./aws-inventory-check.sh > resource-explorer/after-destroy-$(date +%d%m%Y%H%M).txt

        2. PY
            ./aws-inventory-check.sh > path/to/reports/current-status-py-$(date +%d%m%Y%H%M).txt
            ./aws-inventory-check.sh > path/to/reports/after-destroy-py-$(date +%d%m%Y%H%M).txt

=============================================================================================================================

    Gitleaks 

        gitleaks dir <file path> --redact

        gitleaks dir <file path> --redact --report-format json --report-path path/to/reports/gitleaks_local_report_$(date +%d%m%Y%H%M).json


=============================================================================================================================
    
    Semgrep 

        semgrep scan --config p/ci . > path/to/reports/semgrep_findings_p-ci_$(date +%d%m%Y%H%M).txt

        semgrep scan --config p/ci <path-to-file> > path/to/reports/semgrep_findings_p-ci_$(date +%d%m%Y%H%M).txt


=============================================================================================================================

    Remove bad commit from Github

    a. If the commit introduced a file

        git rm --cached aws-provisions/test-files/vpc-lab/sast-ci-test.tf

        update the git ignore

    b. To completely remove a bad commit from history

        git log --oneline -5
                ↓
        identify bad commit
                ↓
        git rebase -i <commit-before-bad-commit>
                ↓
        drop bad commit
                ↓
        git log --oneline -5
                ↓
        verify
                ↓
        git push --force-with-lease origin feature/sast