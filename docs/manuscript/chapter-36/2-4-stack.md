---
title: "Stack"
---

### 2.4 Stack
-   **Pattern:** A Last-In, First-Out (LIFO) data structure. It's excellent for problems involving parentheses matching, backtracking, or maintaining a sequence of elements in a specific order (e.g., monotonic stack).

**Stack Intuition:**

**The Core Idea:** LIFO = Last In, First Out (like a stack of plates)

**When to use:**
1. **Matching pairs:** Parentheses, brackets, tags
2. **Nesting:** Inner-most must close before outer
3. **Backtracking:** Undo operations
4. **Monotonic stack:** Next greater/smaller element

**Key Operations:**
- `push()`: Add to top → O(1)
- `pop()`: Remove from top → O(1)
- `peek()`: View top without removing → O(1)

#### 2.4.1 Valid Parentheses
**Problem:** Given a string `s` containing just the characters `(`, `)`, `{`, `}`, `[` and `]`, determine if the input string is valid.

**Building Intuition:**

**Key Insight:** Last opened bracket must be first closed (LIFO!).

**Example:** `"([])"` 
```
Step 1: '(' → Push to stack: ['(']
Step 2: '[' → Push to stack: ['(', '[']
Step 3: ']' → Matches '[' → Pop: ['(']
Step 4: ')' → Matches '(' → Pop: []
Stack empty → Valid!
```

**Invalid Example:** `"([)]"` 
```
Stack: ['(', '[']
See ')' but top is '[' → Mismatch! Invalid!
```

**Why Stack?**
- Nested structures naturally map to LIFO
- O(n) time, O(n) space
- Elegant matching logic

**Solution:** Use a stack and a hash map. When we see an opening bracket, push it onto the stack. When we see a closing bracket, check if the stack is empty or if the top of the stack is the corresponding opening bracket. If not, the string is invalid. At the end, a valid string will result in an empty stack.

**Pseudocode:**
```
INITIALIZE empty stack
INITIALIZE close_to_open map: ')':'(', '}':'{', ']':'['
FOR each character c in s:
    IF c is a closing bracket (in close_to_open):
        IF stack is not empty AND top of stack == close_to_open[c]:
            POP from stack
        ELSE:
            RETURN False
    ELSE:  // c is an opening bracket
        PUSH c onto stack
RETURN True if stack is empty, else False
```

**Implementation:**
```python
def is_valid(s: str) -> bool:
    """
    Time: O(n) - We process each character once.
    Space: O(n) - In the worst case, we push all characters onto the stack.
    """
    stack = []
    close_to_open = {")": "(", "}": "{", "]": "["}
    for c in s:
        if c in close_to_open:
            if stack and stack[-1] == close_to_open[c]:
                stack.pop()
            else:
                return False
        else:
            stack.append(c)
    return True if not stack else False
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Valid simple | "()" | True | Single pair of matching parentheses |
| Valid complex | "()[]{}" | True | Multiple pairs of matching brackets |
| Valid nested | "{[]}" | True | Properly nested brackets |
| Invalid order | "(]" | False | Mismatched bracket types |
| Invalid incomplete | "((" | False | Unclosed opening brackets |

#### 2.4.2 Add Binary
**Problem:** Given two binary strings `a` and `b`, return their sum as a binary string.

**Solution:** Add from right to left, tracking carry. Can use stack or simply build result string.

**Pseudocode:**
```
INITIALIZE i = len(a) - 1, j = len(b) - 1, carry = 0
INITIALIZE result = []

WHILE i >= 0 OR j >= 0 OR carry:
    digit_a = int(a[i]) if i >= 0 else 0
    digit_b = int(b[j]) if j >= 0 else 0
    
    total = digit_a + digit_b + carry
    char = str(total % 2)
    carry = total // 2
    
    PREPEND char to result
    DECREMENT i, DECREMENT j

RETURN result as string
```

**Implementation:**
```python
def add_binary(a: str, b: str) -> str:
    """
    Time: O(max(len(a), len(b))) - Process all digits.
    Space: O(max(len(a), len(b))) - Result string.
    """
    i, j = len(a) - 1, len(b) - 1
    carry = 0
    result = []
    
    while i >= 0 or j >= 0 or carry:
        digit_a = int(a[i]) if i >= 0 else 0
        digit_b = int(b[j]) if j >= 0 else 0
        
        total = digit_a + digit_b + carry
        result.append(str(total % 2))
        carry = total // 2
        
        i -= 1
        j -= 1
    
    return ''.join(reversed(result))
```

**Trace Table:**
| Test Case | a | b | Output | Explanation |
|-----------|---|---|--------|-------------|
| Basic | "11" | "1" | "100" | 3 + 1 = 4 in binary |
| Different lengths | "1010" | "1011" | "10101" | 10 + 11 = 21 in binary |
| With carry | "111" | "111" | "1110" | 7 + 7 = 14 in binary |
| Zero | "0" | "0" | "0" | 0 + 0 = 0 |
