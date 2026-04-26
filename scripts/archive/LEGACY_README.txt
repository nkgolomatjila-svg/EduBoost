The shell files previously under set-up/, expansion/, project-files/, and remaining-router-files/
were one-off generators targeting a fixed /home/claude/eduboost-sa tree. Application source now
lives under app/ and is maintained directly. Use scripts/setup_dev.sh for local bootstrap and
scripts/db_init.sql + db_seed.sql + db_audit_migration.sql for database provisioning (Docker mounts
these automatically).
