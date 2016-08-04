import java.io.InputStreamReader;
import java.io.PrintStream;
import java.io.UnsupportedEncodingException;

class Main {
    public static void main(String[] args) {

        // Open stdin with UTF-8 support
        InputStreamReader in;
        try {
            in = new InputStreamReader(System.in, "UTF-8");
        } catch (UnsupportedEncodingException e) {
            System.out.println("UTF-8 error\n");
            return;
        }

        // Count characters
        int c = 0;
        int counta = 0;
        int counte = 0;
        while (c != -1) {
            try {
                c = in.read();
            } catch(Exception e) {
                break;
            }
            if (c == 224) { // à
                counta += 1;
            } else if (c == 233) { // é
                counte += 1;
            }
        }

        // Write to stdout with UTF-8 support
        try {
            new PrintStream(System.out, true, "UTF-8").println(counta + " à " + counte + " é\n");
        } catch (UnsupportedEncodingException e) {
            System.out.println("UTF-8 error\n");
            return;
        }
    }
}
