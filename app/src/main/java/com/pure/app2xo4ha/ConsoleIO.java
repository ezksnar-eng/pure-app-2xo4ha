package com.pure.app2xo4ha;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

final class ConsoleIO {

    private ConsoleIO() {
    }

    static final class Out extends OutputStream {
        private final Host.Console console;
        private final boolean isErr;
        private final ByteArrayOutputStream buf = new ByteArrayOutputStream();

        Out(Host.Console console, boolean isErr) {
            this.console = console;
            this.isErr = isErr;
        }

        @Override
        public synchronized void write(int b) {
            buf.write(b);
        }

        @Override
        public synchronized void write(byte[] b, int off, int len) {
            buf.write(b, off, len);
        }

        @Override
        public synchronized void flush() {
            if (buf.size() == 0) {
                return;
            }
            String s;
            try {
                s = new String(buf.toByteArray(), "UTF-8");
            } catch (Exception e) {
                s = buf.toString();
            }
            buf.reset();
            console.write(s, isErr);
        }
    }

    static final class In extends InputStream {
        private final Host.Console console;
        private byte[] cur = new byte[0];
        private int pos = 0;
        private boolean eof = false;

        In(Host.Console console) {
            this.console = console;
        }

        @Override
        public synchronized int read() throws IOException {
            while (pos >= cur.length) {
                if (eof) {
                    return -1;
                }
                String line = console.readLine();
                if (line == null) {
                    eof = true;
                    return -1;
                }
                cur = (line + "\n").getBytes("UTF-8");
                pos = 0;
            }
            return cur[pos++] & 0xff;
        }

        @Override
        public synchronized int read(byte[] b, int off, int len) throws IOException {
            if (len == 0) {
                return 0;
            }
            int first = read();
            if (first == -1) {
                return -1;
            }
            b[off] = (byte) first;
            int n = 1;
            while (n < len && pos < cur.length) {
                b[off + n] = cur[pos++];
                n++;
            }
            return n;
        }
    }
}
