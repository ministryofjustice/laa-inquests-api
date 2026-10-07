# Dry run (ROLLBACK)
PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres -d api -v ON_ERROR_STOP=1 \
  -v evidence_sds_file_name='<sds name>' -v evidence_file_name='<evidence file name>' \
  -v template_sds_file_name='<sds name>' -v template_file_name='<template file name>' \
  -f seed_inq_123_000.sql

# Real run (swaps ROLLBACK for COMMIT)
sed 's/^ROLLBACK;/COMMIT;/' seed_inq_123_000.sql | PGPASSWORD=postgres psql -h localhost -p 5436 -U postgres -d api -v ON_ERROR_STOP=1 \
  -v evidence_sds_file_name='<sds name>' -v evidence_file_name='<evidence file name>' \
  -v template_sds_file_name='<sds name>' -v template_file_name='<template file name>'