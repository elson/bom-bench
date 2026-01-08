---
name: test-driven-development
description: Use PROACTIVELY when implementing any feature or bugfix, before writing implementation code
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

## When to Use

**Always:** New features, bug fixes, refactoring, behavior changes

**Exceptions (ask your human partner):** Throwaway prototypes, generated code, configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it and start over. No keeping as "reference", no "adapting" it. Delete means delete.

## Red-Green-Refactor

**Cycle:** RED (write failing test) → Verify fails correctly → GREEN (minimal code) → Verify passes → REFACTOR (clean up) → Repeat

### RED - Write Failing Test

Write one minimal test showing what should happen. One behavior, clear name, real code (no mocks unless unavoidable).

<Good>
```typescript
test('retries failed operations 3 times', async () => {
  let attempts = 0;
  const operation = () => {
    attempts++;
    if (attempts < 3) throw new Error('fail');
    return 'success';
  };
  const result = await retryOperation(operation);
  expect(result).toBe('success');
  expect(attempts).toBe(3);
});
```
</Good>

<Bad>
```typescript
test('retry works', async () => {
  const mock = jest.fn()
    .mockRejectedValueOnce(new Error())
    .mockResolvedValueOnce('success');
  await retryOperation(mock);
  expect(mock).toHaveBeenCalledTimes(3);
});
```
Vague name, tests mock not code
</Bad>

### Verify RED - Watch It Fail

**MANDATORY.** Run `npm test path/to/test.test.ts`

Confirm: test fails (not errors), failure message expected, fails because feature missing (not typos).

Test passes? You're testing existing behavior. Test errors? Fix error first.

### GREEN - Minimal Code

Write simplest code to pass the test. Don't add features, refactor other code, or "improve" beyond the test.

<Good>
```typescript
async function retryOperation<T>(fn: () => Promise<T>): Promise<T> {
  for (let i = 0; i < 3; i++) {
    try {
      return await fn();
    } catch (e) {
      if (i === 2) throw e;
    }
  }
  throw new Error('unreachable');
}
```
</Good>

<Bad>Over-engineering with options, backoff strategies, callbacks—YAGNI</Bad>

### Verify GREEN - Watch It Pass

**MANDATORY.** Run `npm test path/to/test.test.ts`

Confirm: test passes, other tests still pass, output pristine. Test fails? Fix code. Other tests fail? Fix now.

### REFACTOR - Clean Up

After green only: remove duplication, improve names, extract helpers. Keep tests green, don't add behavior.

### Repeat

Next failing test for next feature.

## Good Tests

- **Minimal:** One thing ("and" in name? split it)
- **Clear:** Name describes behavior (not `test1`)
- **Shows intent:** Demonstrates desired API, not obscure implementation

## Why Order Matters

**Test-first vs Test-after:**
- **Test-first:** Forces you to see failure, proving the test works. Tests answer "What should this do?"
- **Test-after:** Tests pass immediately (proves nothing), biased by implementation. Tests answer "What does this do?"

**Common misconceptions:**
- Manual testing is ad-hoc with no record, can't re-run
- "Deleting work is wasteful" is sunk cost fallacy—keeping unverified code is technical debt
- TDD IS pragmatic: finds bugs before commit, prevents regressions, documents behavior, enables refactoring

## Red Flags - STOP and Start Over

Any of these means: **Delete code. Start over with TDD.**

- Code before test / test after implementation / test passes immediately
- Can't explain why test failed
- "Too simple to test" (simple code breaks, test takes 30 seconds)
- "I already manually tested" (ad-hoc ≠ systematic, no record)
- "Keep as reference" or "adapt existing code" (you'll adapt it = testing after)
- "Deleting X hours is wasteful" (sunk cost fallacy)
- "Need to explore first" (fine—throw away exploration, start with TDD)
- "Test hard = design unclear" (listen to test, hard to test = hard to use)
- "TDD will slow me down" (TDD faster than debugging)
- "Tests after achieve same purpose" / "spirit not ritual" (NO—different goals)
- "TDD is dogmatic, I'm pragmatic" (TDD IS pragmatic)
- "This is different because..."

## Example: Bug Fix

**Bug:** Empty email accepted

**RED:** `test('rejects empty email', () => expect(submitForm({ email: '' }).error).toBe('Email required'))`

**Verify RED:** Run test, confirm fails with "expected 'Email required', got undefined"

**GREEN:** `if (!data.email?.trim()) return { error: 'Email required' };`

**Verify GREEN:** Run test, confirm passes

**REFACTOR:** Extract validation if needed for multiple fields

## Verification Checklist

- [ ] Every new function/method has a test that failed before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass with pristine output
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered

Can't check all boxes? Start over with TDD.

## When Stuck

- **Don't know how to test:** Write wished-for API, write assertion first, ask human partner
- **Test too complicated:** Design too complicated, simplify interface
- **Must mock everything:** Code too coupled, use dependency injection
- **Test setup huge:** Extract helpers; still complex? simplify design

## Debugging

Bug found? Write failing test reproducing it. Follow TDD cycle. Never fix bugs without a test.

## Testing Anti-Patterns

When adding mocks or test utilities, read @testing-anti-patterns.md to avoid common pitfalls:
- Testing mock behavior instead of real behavior
- Adding test-only methods to production classes
- Mocking without understanding dependencies

## Final Rule

```
Production code → test exists and failed first
Otherwise → not TDD
```

No exceptions without your human partner's permission.
