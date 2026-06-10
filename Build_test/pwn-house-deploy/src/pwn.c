#include<stdlib.h>
#include <stdio.h>
#include <unistd.h>

char *chunk_list[0x100];

void menu() {
    puts("1. add");
    puts("2. delete");
    puts("3. edit");
    puts("4. show");
    puts("5. exit");
    puts("choice:");
}

size_t get_num() {
    size_t num;
    scanf("%llu", &num);
    return num;
}

void add_chunk() {
    puts("index:");
    int index = get_num();
    puts("size:");
    size_t size = get_num();
    chunk_list[index] = malloc(size);
}

void delete_chunk() {
    puts("index:");
    int index = get_num();
    free(chunk_list[index]);
}

void edit_chunk() {
    puts("index:");
    int index = get_num();
    puts("length:");
    int length = get_num();
    puts("content:");
    read(0, chunk_list[index], length);
}

void show_chunk() {
    puts("index:");
    int index = get_num();
    puts(chunk_list[index]);
}

int main() {
    setbuf(stdin, NULL);
    setbuf(stdout, NULL);
    setbuf(stderr, NULL);
    printf("[+]Welcome to your new home!\n");
    printf("[+]While visiting, please note that the room numbers are incorrect.\n");
    printf("[+]Wish you can find your own room!!!\n");

    while (1) {
        menu();
        srand(get_num());
        size_t random_num = rand()%4+1;
        switch (random_num) {
            case 1:
                add_chunk();
                break;
            case 2:
                delete_chunk();
                break;
            case 3:
                edit_chunk();
                break;
            case 4:
                show_chunk();
                break;
            case 5:
                exit(0);
            default:
                puts("invalid choice.");
        }
    }
}
