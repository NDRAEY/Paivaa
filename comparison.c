#include <stdint.h>
#include <sys/types.h>
#include <stdio.h>
#include <stdbool.h>
ssize_t i = 120;

int main() {
if(i == 120) {
printf("%s\n", "I = 120!!!");
}
else{
if(i > 120) {
printf("%s\n", "I > 120!!!");
}
else{
if(i < 120) {
printf("%s\n", "I < 120!!!");
}
else{
printf("%s\n", "I not a 120!!!");
}
}
}

}