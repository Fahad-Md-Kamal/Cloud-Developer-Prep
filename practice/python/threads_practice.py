import threading
import time

counter = 0

def increment():
    global counter
    for _ in range(100_000):
        counter += 1

threads = [threading.Thread(target=increment) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(counter)  # you'd expect 400_000 — do you get it?
# (on CPython 3.12 this one usually DOES print 400000 -- see visual_race_demo()
# below for why, and for a version that actually shows the race happening)


def visual_race_demo():
    """Same read-modify-write race, slowed down and printed step by step
    so the lost update is visible instead of just a wrong final number."""
    shared = 0
    print("--- Visual race condition demo (2 threads, 5 increments each) ---\n")

    def worker(name):
        nonlocal shared
        for _ in range(5):
            read_value = shared
            print(f"[{name}] READ  counter = {read_value}")
            time.sleep(0.05)  # widen the window so both threads read before either writes
            new_value = read_value + 1
            shared = new_value
            print(f"[{name}] WRITE counter = {new_value}")
            time.sleep(0.05)

    t1 = threading.Thread(target=worker, args=("Thread-A",))
    t2 = threading.Thread(target=worker, args=("Thread-B",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print(f"\nFinal counter = {shared}  (expected 10 if no updates were lost)")


if __name__ == "__main__":
    visual_race_demo()