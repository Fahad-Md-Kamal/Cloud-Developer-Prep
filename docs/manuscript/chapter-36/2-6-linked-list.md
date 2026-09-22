---
title: "Linked List"
---

### 2.6 Linked List
-   **Pattern:** A linear data structure where elements are not stored at contiguous memory locations. They are linked using pointers. Problems often involve pointer manipulation, cycles, or reversing the list.

**Linked List Intuition:**

**Key Concepts:**
1. **No random access:** Must traverse from head (O(n))
2. **Pointer manipulation:** Changing `.next` links
3. **Common patterns:**
   - Dummy node (simplifies edge cases)
   - Fast/slow pointers (cycle detection, middle)
   - Reverse pointers (reverse list)

**When to use:**
- Dynamic size, frequent insertions/deletions
- No need for random access
- Cycle detection problems

```python
# Definition for singly-linked list.
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next
```

#### 2.6.1 Reverse Linked List
**Problem:** Given the `head` of a singly linked list, reverse the list, and return the *reversed list*.

**Building Intuition:**

**Visual:** `1 → 2 → 3 → None` becomes `None ← 1 ← 2 ← 3`

**The Trick:** For each node, point it backwards instead of forwards.

**Three Pointers:**
1. `prev` = where we came from (initially None)
2. `curr` = current node being processed
3. `nxt` = save next before we lose it

**Step-by-step:** `1 → 2 → 3`
```
Step 1: prev=None, curr=1, nxt=2
        1.next = None (reverse)
        prev=1, curr=2

Step 2: prev=1, curr=2, nxt=3
        2.next = 1 (reverse)
        prev=2, curr=3

Step 3: prev=2, curr=3, nxt=None
        3.next = 2 (reverse)
        prev=3, curr=None

Return prev (new head)
```

**Why Three Pointers?**
- Need to save next before breaking link
- Need prev to point current node back
- One pass: O(n) time, O(1) space

**Solution:** The iterative approach uses three pointers: `prev` (initially `None`), `curr` (starts at `head`), and `nxt` (to temporarily store the next node). For each node, we:
1. Save the next node (`nxt = curr.next`)
2. Reverse the pointer (`curr.next = prev`)
3. Move `prev` and `curr` forward

**Algorithm:**
- Initialize `prev = None` and `curr = head`
- While `curr` is not None:
  - Store `curr.next` in `nxt`
  - Point `curr.next` to `prev` (reversing the link)
  - Move `prev` to `curr` and `curr` to `nxt`
- Return `prev` (the new head)

**Pseudocode:**
```
INITIALIZE prev = None, curr = head
WHILE curr is not None:
    nxt = curr.next  // Save next node
    curr.next = prev  // Reverse pointer
    prev = curr  // Move prev forward
    curr = nxt  // Move curr forward
RETURN prev  // New head
```

**Implementation:**
```python
def reverse_list(head: ListNode) -> ListNode:
    """
    Time: O(n) - We visit each node once.
    Space: O(1) - We only use a few pointers.
    """
    prev, curr = None, head
    while curr:
        nxt = curr.next  # Store the next node
        curr.next = prev # Reverse the pointer
        prev = curr      # Move prev up
        curr = nxt       # Move curr up
    return prev
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [1,2,3,4,5] | [5,4,3,2,1] | Entire list reversed |
| Two nodes | [1,2] | [2,1] | Simple two-node reversal |
| Single node | [1] | [1] | Single node stays same |
| Empty list | [] | [] | Empty list returns empty |

#### 2.6.2 Merge Two Sorted Lists
**Problem:** You are given the heads of two sorted linked lists `list1` and `list2`. Merge the two lists into one **sorted** list.

**Solution:** Use a dummy node as a placeholder for the head of the merged list. This simplifies edge cases (like when one list is empty). Use a `tail` pointer to build the new list.

**Algorithm:**
1. Create a dummy node and a tail pointer
2. While both lists have nodes:
   - Compare the current values
   - Append the smaller node to tail
   - Advance the pointer of the list from which we took the node
3. Attach any remaining nodes from the non-empty list
4. Return `dummy.next` (the actual head)

**Pseudocode:**
```
INITIALIZE dummy = new ListNode()
INITIALIZE tail = dummy

WHILE list1 is not None AND list2 is not None:
    IF list1.val < list2.val:
        tail.next = list1
        list1 = list1.next
    ELSE:
        tail.next = list2
        list2 = list2.next
    tail = tail.next

// Append remainder
tail.next = list1 OR list2
RETURN dummy.next
```

**Implementation:**
```python
def merge_two_lists(list1: ListNode, list2: ListNode) -> ListNode:
    """
    Time: O(n + m) - We visit each node in both lists.
    Space: O(1) - We are rearranging the existing nodes.
    """
    dummy = ListNode()
    tail = dummy
    
    while list1 and list2:
        if list1.val < list2.val:
            tail.next = list1
            list1 = list1.next
        else:
            tail.next = list2
            list2 = list2.next
        tail = tail.next
        
    # Append the remainder of the non-empty list
    tail.next = list1 or list2
    
    return dummy.next
```

**Trace Table:**
| Test Case | Input (list1) | Input (list2) | Output | Explanation |
|-----------|---------------|---------------|--------|-------------|
| Basic | [1,2,4] | [1,3,4] | [1,1,2,3,4,4] | Merged sorted lists |
| One empty | [] | [0] | [0] | Empty list merged with non-empty |
| Both empty | [] | [] | [] | Two empty lists |
| Different lengths | [1] | [2,3,4] | [1,2,3,4] | Lists of different lengths merged |

#### 2.6.3 Reorder List
**Problem:** You are given the head of a singly linked list. The list can be represented as: `L0 → L1 → … → Ln-1 → Ln`. Reorder the list to be: `L0 → Ln → L1 → Ln-1 → L2 → Ln-2 → …`

**Solution:** This problem combines three classic linked list techniques:
1. **Find the middle** using slow/fast pointers
2. **Reverse the second half** of the list
3. **Merge the two halves** by alternating nodes

**Algorithm:**
- Use slow/fast pointers to find the middle
- Split the list into two halves at the middle
- Reverse the second half
- Merge by taking alternating nodes from each half

**Pseudocode:**
```
// 1. Find middle
INITIALIZE slow = head, fast = head.next
WHILE fast is not None AND fast.next is not None:
    slow = slow.next
    fast = fast.next.next

// 2. Reverse second half
second = slow.next
prev = slow.next = None
WHILE second is not None:
    tmp = second.next
    second.next = prev
    prev = second
    second = tmp

// 3. Merge two halves
first = head, second = prev
WHILE second is not None:
    tmp1 = first.next
    tmp2 = second.next
    first.next = second
    second.next = tmp1
    first = tmp1
    second = tmp2
```

**Implementation:**
```python
def reorder_list(head: ListNode) -> None:
    """
    Do not return anything, modify head in-place instead.
    Time: O(n) - Each step (find middle, reverse, merge) is O(n).
    Space: O(1) - In-place modification.
    """
    # 1. Find middle
    slow, fast = head, head.next
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        
    # 2. Reverse second half
    second = slow.next
    prev = slow.next = None
    while second:
        tmp = second.next
        second.next = prev
        prev = second
        second = tmp
        
    # 3. Merge two halves
    first, second = head, prev
    while second:
        tmp1, tmp2 = first.next, second.next
        first.next = second
        second.next = tmp1
        first, second = tmp1, tmp2
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [1,2,3,4] | [1,4,2,3] | Reordered by alternating from ends |
| Odd length | [1,2,3,4,5] | [1,5,2,4,3] | Middle element stays in place |
| Two nodes | [1,2] | [1,2] | Already in correct order |
| Single node | [1] | [1] | No reordering needed |

#### 2.6.4 Middle of the Linked List
**Problem:** Given the head of a singly linked list, return the middle node. If there are two middle nodes, return the second middle node.

**Solution:** Use slow and fast pointers. Fast moves twice as fast as slow.

**Pseudocode:**
```
INITIALIZE slow = head, fast = head
WHILE fast is not None AND fast.next is not None:
    slow = slow.next
    fast = fast.next.next
RETURN slow
```

**Implementation:**
```python
def middle_node(head: ListNode) -> ListNode:
    """
    Time: O(n) - Single pass through list.
    Space: O(1) - Only two pointers.
    """
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    return slow
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Odd length | [1,2,3,4,5] | [3,4,5] | Middle node is 3 |
| Even length | [1,2,3,4,5,6] | [4,5,6] | Second middle node |
| Two nodes | [1,2] | [2] | Second of two nodes |
| Single node | [1] | [1] | Single node is middle |

#### 2.6.5 Linked List Cycle II
**Problem:** Given the head of a linked list, return the node where the cycle begins. If there is no cycle, return `null`.

**Solution:** Use Floyd's algorithm: detect cycle with slow/fast pointers, then find entry point.

**Pseudocode:**
```
// Phase 1: Detect cycle
INITIALIZE slow = head, fast = head
WHILE fast is not None AND fast.next is not None:
    slow = slow.next
    fast = fast.next.next
    IF slow == fast:
        BREAK
ELSE:
    RETURN None  // No cycle

// Phase 2: Find entry point
INITIALIZE slow = head
WHILE slow != fast:
    slow = slow.next
    fast = fast.next
RETURN slow
```

**Implementation:**
```python
def detect_cycle(head: ListNode) -> ListNode:
    """
    Time: O(n) - Two passes through list.
    Space: O(1) - Only two pointers.
    """
    slow = fast = head
    
    # Detect cycle
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            break
    else:
        return None
    
    # Find entry point
    slow = head
    while slow != fast:
        slow = slow.next
        fast = fast.next
    
    return slow
```

**Trace Table:**
| Test Case | Input | Pos | Output | Explanation |
|-----------|-------|-----|--------|-------------|
| Cycle at 1 | [3,2,0,-4] | 1 | node(2) | Cycle starts at node with value 2 |
| Cycle at 0 | [1,2] | 0 | node(1) | Cycle starts at head |
| No cycle | [1] | -1 | null | No cycle exists |
| Self loop | [1,2,3] | 2 | node(3) | Last node points to itself |

#### 2.6.6 Reverse Linked List II
**Problem:** Given the head of a singly linked list and two integers `left` and `right`, reverse the nodes from position `left` to position `right`.

**Solution:** Find the portion to reverse, reverse it, and reconnect.

**Pseudocode:**
```
INITIALIZE dummy = new ListNode(0, head)
INITIALIZE leftPrev = dummy

// Move to node before left position
FOR i from 0 to left - 1:
    leftPrev = leftPrev.next

// Reverse from left to right
curr = leftPrev.next
FOR i from 0 to right - left:
    temp = curr.next
    curr.next = temp.next
    temp.next = leftPrev.next
    leftPrev.next = temp

RETURN dummy.next
```

**Implementation:**
```python
def reverse_between(head: ListNode, left: int, right: int) -> ListNode:
    """
    Time: O(n) - Single pass through list.
    Space: O(1) - In-place reversal.
    """
    dummy = ListNode(0, head)
    left_prev = dummy
    
    # Move to node before left position
    for _ in range(left - 1):
        left_prev = left_prev.next
    
    # Reverse the sublist
    curr = left_prev.next
    for _ in range(right - left):
        temp = curr.next
        curr.next = temp.next
        temp.next = left_prev.next
        left_prev.next = temp
    
    return dummy.next
```

**Trace Table:**
| Test Case | Input | left | right | Output | Explanation |
|-----------|-------|------|-------|--------|-------------|
| Basic | [1,2,3,4,5] | 2 | 4 | [1,4,3,2,5] | Reversed middle portion |
| Full list | [1,2,3] | 1 | 3 | [3,2,1] | Reversed entire list |
| Single node | [5] | 1 | 1 | [5] | No reversal needed |
| Two nodes | [3,5] | 1 | 2 | [5,3] | Reversed both nodes |

#### 2.6.7 Remove Nth Node From End of List
**Problem:** Given the `head` of a linked list, remove the `n`-th node from the end of the list and return its head.

**Solution:** The two-pointer technique allows us to find the nth node from the end in one pass. We use a dummy node to handle edge cases (like removing the head).

**Algorithm:**
1. Create a dummy node pointing to head
2. Initialize `left` at dummy and `right` at head
3. Move `right` forward `n` steps
4. Move both `left` and `right` until `right` reaches the end
5. Now `left.next` is the node to remove, so skip it: `left.next = left.next.next`

**Pseudocode:**
```
INITIALIZE dummy = new ListNode(0, head)
INITIALIZE left = dummy, right = head

// Move right n steps ahead
WHILE n > 0 AND right is not None:
    right = right.next
    DECREMENT n

// Move both pointers until right reaches end
WHILE right is not None:
    left = left.next
    right = right.next

// Delete the node
left.next = left.next.next
RETURN dummy.next
```

**Implementation:**
```python
def remove_nth_from_end(head: ListNode, n: int) -> ListNode:
    """
    Time: O(L) - Where L is the length of the list.
    Space: O(1) - Only pointers are used.
    """
    dummy = ListNode(0, head)
    left = dummy
    right = head
    
    while n > 0 and right:
        right = right.next
        n -= 1
        
    while right:
        left = left.next
        right = right.next
        
    # Delete the node
    left.next = left.next.next
    return dummy.next
```

**Trace Table:**
| Test Case | Input | n | Output | Explanation |
|-----------|-------|---|--------|-------------|
| Remove middle | [1,2,3,4,5] | 2 | [1,2,3,5] | Remove 4 (2nd from end) |
| Remove head | [1] | 1 | [] | Single node removed |
| Remove last | [1,2] | 1 | [1] | Remove last node |
| Remove first | [1,2] | 2 | [2] | Remove first node |

#### 2.6.5 Linked List Cycle
**Problem:** Given `head`, the head of a linked list, determine if the linked list has a cycle in it.

**Solution:** Floyd's Cycle Detection Algorithm (Tortoise and Hare). Use two pointers moving at different speeds. If there's a cycle, they will eventually meet.

**Algorithm:**
- Initialize slow and fast pointers at head
- Move slow one step and fast two steps
- If fast catches up to slow, there's a cycle
- If fast reaches the end (None), there's no cycle

**Why it works:** In a cycle, the fast pointer will eventually "lap" the slow pointer. The distance between them decreases by 1 each iteration until they meet.

**Pseudocode:**
```
INITIALIZE slow = head, fast = head
WHILE fast is not None AND fast.next is not None:
    slow = slow.next  // Move one step
    fast = fast.next.next  // Move two steps
    IF slow == fast:
        RETURN True  // Cycle detected
RETURN False  // No cycle
```

**Implementation:**
```python
def has_cycle(head: ListNode) -> bool:
    """
    Time: O(n) - In the worst case, we traverse the entire list.
    Space: O(1) - Only two pointers are used.
    """
    slow, fast = head, head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True
    return False
```

**Trace Table:**
| Test Case | Input (list → cycle pos) | Output | Explanation |
|-----------|--------------------------|--------|-------------|
| Has cycle | [3,2,0,-4] → pos 1 | True | Tail connects to node index 1 |
| Has cycle (self) | [1,2] → pos 0 | True | Tail connects to head |
| No cycle | [1] | False | Single node with no cycle |
| No cycle (multiple) | [1,2,3] | False | Linear list with no cycle |

#### 2.6.6 Merge K Sorted Lists
**Problem:** You are given an array of `k` linked-lists `lists`, each linked-list is sorted in ascending order. Merge all the linked-lists into one sorted linked-list and return it.

**Solution:** Use a min-heap to efficiently get the smallest element among all k lists. The heap maintains the current heads of each list that haven't been processed yet.

**Algorithm:**
1. Add the first node from each non-empty list to a min-heap
2. While the heap is not empty:
   - Pop the smallest node
   - Add it to the result list
   - If that node has a next node, push it to the heap
3. Return the merged list

**Why a heap?** Comparing all k heads each time would be O(k), leading to O(N*k) time. The heap reduces this to O(log k) per operation, giving us O(N log k) overall.

**Pseudocode:**
```
INITIALIZE min_heap = empty heap
FOR each list in lists:
    IF list is not empty:
        PUSH (list.val, index, list) to min_heap

INITIALIZE dummy = new ListNode()
INITIALIZE tail = dummy

WHILE min_heap is not empty:
    (val, index, node) = POP from min_heap
    tail.next = node
    tail = tail.next
    IF node.next is not None:
        PUSH (node.next.val, index, node.next) to min_heap

RETURN dummy.next
```

**Implementation:**
```python
def merge_k_lists(lists: list[ListNode]) -> ListNode:
    """
    Time: O(k * N) - For each of the N nodes we scan k list heads to find the minimum.
    Space: O(1) - Aside from the output links.
    """
    nodes = list(lists)
    dummy = ListNode()
    tail = dummy

    while True:
        min_index = -1
        min_value = None
        for i, node in enumerate(nodes):
            if node is None:
                continue
            if min_index == -1 or node.val < min_value:
                min_index = i
                min_value = node.val

        if min_index == -1:
            break

        node = nodes[min_index]
        tail.next = node
        tail = tail.next
        nodes[min_index] = node.next

    return dummy.next
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [[1,4,5],[1,3,4],[2,6]] | [1,1,2,3,4,4,5,6] | Merged 3 sorted lists |
| Empty lists | [] | [] | No lists to merge |
| One empty | [[],[1]] | [1] | One empty, one with single element |
| Single list | [[1,2,3]] | [1,2,3] | Single list returned as-is |
