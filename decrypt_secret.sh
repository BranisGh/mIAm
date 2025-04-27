#!/bin/sh

# Decrypt the file
mkdir $HOME/secrets
# --batch to prevent interactive command
# --yes to assume "yes" for questions
gpg --quiet --batch --yes --decrypt --passphrase="miam-service-secure-key-2025" \
--output $HOME/secrets/gcp_service_account_key.json gcp_service_account_key.json.gpg
