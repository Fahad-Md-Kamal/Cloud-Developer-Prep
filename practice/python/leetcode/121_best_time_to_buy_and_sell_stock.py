class Solution:
    def maxProfit(self, prices: list[int]) -> int:
        lp , rp = 0, 1
        mxPr = 0
        while rp < len(prices):
            if prices[rp] < prices[lp]:
                lp = rp
            profit = prices[rp] - prices[lp]
            mxPr = max(profit, mxPr)
            rp += 1
        return mxPr


if __name__ == "__main__":
    test_cases = [
        ([7, 1, 5, 3, 6, 4], 5),
        ([7, 6, 4, 3, 1], 0),
        ([1, 2, 3, 4, 5], 4),
        ([1], 0),
        ([1, 2], 1),
        ([2, 1], 0),
        ([3, 3, 3, 3], 0),
        ([2, 4, 1], 2),
        ([3, 2, 6, 5, 0, 3], 4),
        ([5, 5, 5, 5, 5], 0),
        ([10, 1, 10, 1, 10], 9),
        ([1, 7, 2, 8, 1, 9], 8),
        ([9, 8, 7, 6, 5, 4, 3, 2, 1], 0),
        ([1, 1, 1, 1, 2], 1),
        ([2, 1, 2, 1, 2], 1),
        ([100, 180, 260, 310, 40, 535, 695], 655),
        ([1, 9, 2, 8, 3, 7, 4, 6, 5], 8),
        ([0, 0, 0, 1], 1),
        ([6, 1, 3, 2, 4, 7], 6),
        ([2, 1, 4], 3),
    ]

    solution = Solution()
    for i, (prices, expected) in enumerate(test_cases, start=1):
        actual = solution.maxProfit(prices)
        assert actual == expected, (
            f"Test {i} failed: maxProfit({prices!r}) = {actual}, expected {expected}"
        )
        print(f"Test {i:2d} passed: maxProfit({prices!r}) = {actual}")

    print(f"\nAll {len(test_cases)} test cases passed!")
