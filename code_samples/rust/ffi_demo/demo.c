/* A C program that uses the Rust library. Build and run with ./build.sh */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct { double x; double y; } Point;
typedef struct Counter Counter; /* opaque: C never sees the fields */
typedef void (*Visitor)(int value, void *user);

int demo_add(int a, int b);
int demo_distance(const Point *p, const Point *q, double *out);
char *demo_greet(const char *name);
void demo_string_free(char *s);
Counter *demo_counter_new(void);
uint64_t demo_counter_incr(Counter *c);
void demo_counter_free(Counter *c);
void demo_for_each(const int *values, size_t len, Visitor visit, void *user);
int demo_checked_divide(int a, int b, int *out);
void demo_panics(void);
int demo_sum(int n, ...);

static void sum_visitor(int value, void *user) { *(int *)user += value; }

int main(int argc, char **argv) {
    printf("demo_add(2, 3) = %d\n", demo_add(2, 3));

    Point p = {0.0, 0.0}, q = {3.0, 4.0};
    double d = 0.0;
    int rc = demo_distance(&p, &q, &d);
    printf("demo_distance -> rc=%d distance=%.1f\n", rc, d);
    printf("demo_distance(NULL) -> rc=%d\n", demo_distance(NULL, &q, &d));

    char *greeting = demo_greet("C");
    printf("%s\n", greeting);
    demo_string_free(greeting); /* freed by RUST, because Rust allocated it */

    Counter *c = demo_counter_new();
    demo_counter_incr(c);
    printf("counter = %llu\n", (unsigned long long)demo_counter_incr(c));
    demo_counter_free(c);

    int values[] = {1, 2, 3, 4};
    int total = 0;
    demo_for_each(values, 4, sum_visitor, &total);
    printf("callback sum = %d\n", total);

    int out = 0;
    printf("checked_divide(10, 2) -> rc=%d out=%d\n", demo_checked_divide(10, 2, &out), out);
    printf("checked_divide(1, 0) -> rc=%d\n", demo_checked_divide(1, 0, &out));

    printf("demo_sum(3, 10, 20, 30) = %d\n", demo_sum(3, 10, 20, 30));

    if (argc > 1) { /* ./demo panic : a Rust panic inside extern "C" aborts the process */
        printf("calling demo_panics()...\n");
        fflush(stdout);
        demo_panics();
        printf("never reached\n");
    }
    return 0;
}
