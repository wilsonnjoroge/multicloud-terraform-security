
============================================================================================================================

The default directory for keeping the inventory checks eg 

    AWS Resource Explorer

        1. SH
            ./aws-inventory-check.sh > resource-explorer/before-apply-$(date +%d%m%Y%H%M).txt
            ./aws-inventory-check.sh > resource-explorer/after-apply-$(date +%d%m%Y%H%M).txt

            ./aws-inventory-check.sh > resource-explorer/before-destroy-$(date +%d%m%Y%H%M).txt
            ./aws-inventory-check.sh > resource-explorer/after-destroy-$(date +%d%m%Y%H%M).txt

        2. PY
            ./aws-inventory-check.sh > resource-explorer/after-destroy-py-$(date +%d%m%Y%H%M).txt
            ./aws-inventory-check.sh > ../resource-explorer/current-status-py-$(date +%d%m%Y%H%M).txt
    
    Semgrep p/ci config on curremt dir
        semgrep scan --config p/ci . > ./aws-provisions/vpc-lab/resource-explorer/semgrep_findings_p-ci_$(date +%d%m%Y%H%M).txt

        semgrep scan --config p/ci <path-to-file> > ./aws-provisions/vpc-lab/resource-explorer/semgrep_findings_p-ci_$(date +%d%m%Y%H%M).txt


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