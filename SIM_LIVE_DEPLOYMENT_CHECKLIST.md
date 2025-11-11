# SIM/LIVE Mode Separation - Deployment Checklist

## Pre-Deployment Verification

### 1. Code Review
- [ ] Review all modified files for correctness
- [ ] Verify no hardcoded values (use config)
- [ ] Check error handling is comprehensive
- [ ] Ensure logging is appropriate (not too verbose)
- [ ] Verify thread safety (Qt marshaling)

### 2. Database Schema
- [ ] Verify `mode` column exists in TradeRecord
- [ ] Verify `mode` column exists in OrderRecord
- [ ] Verify `mode` column exists in AccountBalance
- [ ] Check indexes on `mode` columns
- [ ] Test query performance with mode filter

### 3. Configuration
- [ ] Set `LIVE_ACCOUNT` in `config/settings.py` to correct value
- [ ] Verify DTC connection settings
- [ ] Check database connection string
- [ ] Review logging configuration

### 4. Dependencies
- [ ] All required modules installed
- [ ] Python 3.10+ confirmed
- [ ] PyQt6 working correctly
- [ ] SQLModel version compatible

## Testing Phase

### 5. Unit Tests (if available)
- [ ] Run existing test suite
- [ ] Add mode separation tests
- [ ] Test mode detection logic
- [ ] Test state manager methods

### 6. Integration Tests
- [ ] Test with Sierra Chart SIM account
- [ ] Test with Sierra Chart LIVE account (in test environment!)
- [ ] Test mode switching
- [ ] Test balance updates
- [ ] Test statistics filtering

### 7. Manual Testing
- [ ] Complete all 8 test scenarios from testing guide
- [ ] Verify database queries show correct mode filtering
- [ ] Test dialog warnings appear correctly
- [ ] Test empty state display
- [ ] Test rapid mode switching

### 8. Performance Testing
- [ ] Load test with 1000+ historical trades
- [ ] Stress test rapid mode switching
- [ ] Monitor memory usage
- [ ] Check UI responsiveness
- [ ] Verify no race conditions

### 9. Edge Case Testing
- [ ] Empty account strings
- [ ] Unknown account strings
- [ ] Missing state manager (graceful degradation)
- [ ] Database errors (safe fallbacks)
- [ ] Concurrent position updates

## Deployment Steps

### 10. Backup
- [ ] Backup current production code
- [ ] Backup production database
- [ ] Document rollback procedure
- [ ] Test backup restoration process

### 11. Database Migration
```sql
-- Verify mode columns exist
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name IN ('traderecord', 'orderrecord', 'accountbalance')
  AND column_name = 'mode';

-- Add indexes if not present
CREATE INDEX IF NOT EXISTS idx_traderecord_mode ON traderecord(mode);
CREATE INDEX IF NOT EXISTS idx_orderrecord_mode ON orderrecord(mode);
CREATE INDEX IF NOT EXISTS idx_accountbalance_mode ON accountbalance(mode);

-- Set default mode for existing records
UPDATE traderecord SET mode = 'SIM' WHERE mode IS NULL;
UPDATE orderrecord SET mode = 'SIM' WHERE mode IS NULL;
UPDATE accountbalance SET mode = 'LIVE' WHERE mode IS NULL;
```
- [ ] Run migration script
- [ ] Verify data integrity
- [ ] Test query performance after migration

### 12. Code Deployment
- [ ] Deploy to staging environment first
- [ ] Test in staging
- [ ] Get approval from stakeholders
- [ ] Deploy to production
- [ ] Verify deployment successful

### 13. Configuration
- [ ] Update `LIVE_ACCOUNT` value in production config
- [ ] Verify environment variables
- [ ] Check logging configuration
- [ ] Enable performance monitoring

## Post-Deployment Verification

### 14. Smoke Tests
- [ ] App starts successfully
- [ ] Connects to Sierra Chart
- [ ] Mode detected correctly
- [ ] Positions open/close normally
- [ ] Statistics display correctly

### 15. Monitoring
- [ ] Check application logs for errors
- [ ] Monitor database query performance
- [ ] Watch for memory leaks
- [ ] Track mode switch frequency
- [ ] Monitor dialog appearances (blocked trades)

### 16. User Acceptance
- [ ] Demo to stakeholders
- [ ] Train users on mode precedence rules
- [ ] Provide testing guide
- [ ] Collect feedback
- [ ] Address any issues

## Rollback Plan

### If Issues Arise

**Level 1 (Configuration Rollback)**
- [ ] Revert `LIVE_ACCOUNT` config
- [ ] Restart application
- [ ] Verify fallback behavior

**Level 2 (Code Rollback)**
- [ ] Restore from backup
- [ ] Restart application
- [ ] Run verification tests
- [ ] Document issue

**Level 3 (Database Rollback)**
- [ ] Stop application
- [ ] Restore database from backup
- [ ] Restore code from backup
- [ ] Restart application
- [ ] Verify data integrity

## Production Monitoring

### 17. Ongoing Monitoring (First Week)
- [ ] Daily log review
- [ ] Performance metrics tracking
- [ ] User feedback collection
- [ ] Bug report triage
- [ ] Database health checks

### 18. Key Metrics to Watch
- [ ] Mode detection accuracy (should be 100%)
- [ ] Blocked trade frequency (should be rare)
- [ ] Balance update latency (should be < 100ms)
- [ ] Statistics query time (should be < 500ms)
- [ ] Dialog appearance frequency (user feedback metric)

### 19. Alert Thresholds
- [ ] Set up alert: Mode detection failure > 0%
- [ ] Set up alert: Database query time > 1s
- [ ] Set up alert: Memory usage increase > 20%
- [ ] Set up alert: Application crashes
- [ ] Set up alert: Race condition errors

## Documentation

### 20. User Documentation
- [ ] Update user manual with mode precedence rules
- [ ] Add FAQ for common mode questions
- [ ] Create quick reference guide
- [ ] Record demo video
- [ ] Update training materials

### 21. Developer Documentation
- [ ] Update architecture diagrams
- [ ] Document new APIs
- [ ] Add troubleshooting guide
- [ ] Update README files
- [ ] Create maintenance runbook

## Sign-off

### Development Team
- [ ] Implementation complete
- [ ] Code reviewed
- [ ] Tests passing
- [ ] Documentation complete

**Developer**: _______________  **Date**: ___________

### QA Team
- [ ] Test plan executed
- [ ] All scenarios pass
- [ ] Performance acceptable
- [ ] Issues documented

**QA Lead**: _______________  **Date**: ___________

### Product Owner
- [ ] Functionality verified
- [ ] User experience acceptable
- [ ] Business requirements met
- [ ] Ready for production

**Product Owner**: _______________  **Date**: ___________

### Deployment Team
- [ ] Deployment plan approved
- [ ] Rollback plan tested
- [ ] Monitoring configured
- [ ] Backup verified

**DevOps Lead**: _______________  **Date**: ___________

## Final Go/No-Go Decision

**Deployment Date**: ___________
**Deployment Time**: ___________

**Decision**: [ ] GO [ ] NO-GO

**Reasons if NO-GO**:
```
(Document any blockers or issues that prevent deployment)
```

**Sign-off Authority**: _______________  **Date**: ___________

---

## Post-Deployment Notes

### Issues Encountered
```
(Document any issues found after deployment)
```

### Lessons Learned
```
(Document improvements for future deployments)
```

### Follow-up Items
- [ ] Item 1: _______________
- [ ] Item 2: _______________
- [ ] Item 3: _______________

**Deployment Status**: [ ] Successful [ ] Partial [ ] Rolled Back

**Final Notes**:
```
(Any additional context or information)
```

---

**Checklist Version**: 1.0
**Last Updated**: 2025-11-10
**Next Review**: ___________
