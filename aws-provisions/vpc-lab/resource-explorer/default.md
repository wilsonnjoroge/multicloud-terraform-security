The default directory for keeping the inventory checks eg 

    AWS Resource Explorer
        ./aws-inventory-check.sh > resource-explorer/before-apply-$(date +%d%m%Y%H%M).tx
        ./aws-inventory-check.sh > resource-explorer/after-apply-$(date +%d%m%Y%H%M).tx

        ./aws-inventory-check.sh > resource-explorer/before-destroy-$(date +%d%m%Y%H%M).tx
        ./aws-inventory-check.sh > resource-explorer/after-destroy-$(date +%d%m%Y%H%M).tx
    
    Semgrep p/ci config on curremt dir
        semgrep scan --config p/ci . > ./aws-provisions/vpc-lab/resource-explorer/semgrep_findings_p-ci_$(date +%d%m%Y%H%M).txt

        semgrep scan --config p/ci <path-to-file> > ./aws-provisions/vpc-lab/resource-explorer/semgrep_findings_p-ci_$(date +%d%m%Y%H%M).txt