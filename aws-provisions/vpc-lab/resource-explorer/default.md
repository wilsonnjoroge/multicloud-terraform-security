The default directory for keeping the inventory checks eg 

    ./aws-inventory-check.sh > resource-explorer/before-apply-$(date +%d%m%Y%H%M).tx
    ./aws-inventory-check.sh > resource-explorer/after-apply-$(date +%d%m%Y%H%M).tx

    ./aws-inventory-check.sh > resource-explorer/before-destroy-$(date +%d%m%Y%H%M).tx
    ./aws-inventory-check.sh > resource-explorer/after-destroy-$(date +%d%m%Y%H%M).tx
    