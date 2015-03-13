int main()
{
    setuid(0);
    system("/bin/chmod -R a+r /tmp/box/");
    return 0;
}
