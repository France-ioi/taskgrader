// Copyright (c) 2015 France-IOI, MIT license
//
// http://opensource.org/licenses/MIT

// This tool changes the rights on the isolate folder /tmp/box/.
// It's meant to be used with suid root (scripts can't be set as suid root).


int main()
{
    setuid(0);
    system("/bin/chmod -R a+r /tmp/box/");
    return 0;
}
