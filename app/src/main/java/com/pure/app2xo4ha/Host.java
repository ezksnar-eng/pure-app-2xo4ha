package com.pure.app2xo4ha;

import android.content.Context;
import android.content.res.AssetManager;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.concurrent.LinkedBlockingQueue;

public final class Host {

    public interface Listener {
        void onAppend(String text);
    }

    public static class Console {
        public void write(String text, boolean isError) {
            append(text);
        }

        public String readLine() {
            try {
                return LINES.take();
            } catch (InterruptedException e) {
                return null;
            }
        }
    }

    private static final String ENTRY = "main.py";
    private static final String LIVE_BASE = "https://raw.githubusercontent.com/ezksnar-eng/pure-app-2xo4ha/main/live/";
    private static final long BUNDLED_VERSION = 1790044195L;
    private static final boolean USES_FILES = true;
    private static final int MAX_LOG = 300000;

    private static final StringBuilder LOG = new StringBuilder();
    private static final LinkedBlockingQueue<String> LINES = new LinkedBlockingQueue<String>();
    private static Listener listener;
    private static boolean started = false;
    private static boolean finished = false;

    private Host() {
    }

    public static synchronized boolean isFinished() {
        return finished;
    }

    /** Attach a listener; it immediately receives everything printed so far. */
    public static synchronized void attach(Listener l) {
        listener = l;
        if (l != null && LOG.length() > 0) {
            l.onAppend(LOG.toString());
        }
    }

    public static void submit(String line) {
        LINES.offer(line);
    }

    static synchronized void append(String s) {
        LOG.append(s);
        if (LOG.length() > MAX_LOG) {
            LOG.delete(0, LOG.length() - MAX_LOG / 2);
        }
        if (listener != null) {
            listener.onAppend(s);
        }
    }

    /** Starts the program once per process. */
    public static synchronized void start(Context ctx) {
        if (started) {
            return;
        }
        started = true;
        final Context app = ctx.getApplicationContext();
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                runAll(app);
            }
        }, "pure-host");
        t.setDaemon(true);
        t.start();
    }

    private static void runAll(Context ctx) {
        try {
            File dir = new File(ctx.getFilesDir(), "code");
            String entry = ENTRY;
            if (USES_FILES) {
                File live = new File(ctx.getFilesDir(), "live");
                live.mkdirs();
                long have = LiveUpdater.readVersion(live);
                if (have < BUNDLED_VERSION || !dir.exists()) {
                    copyAssets(ctx.getAssets(), "code", dir);
                    LiveUpdater.writeState(live, BUNDLED_VERSION, ENTRY);
                    have = BUNDLED_VERSION;
                }
                if (LIVE_BASE.length() > 0) {
                    append("\u062c\u0627\u0631\u064a \u0627\u0644\u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u0644\u062a\u062d\u062f\u064a\u062b\u0627\u062a...\n");
                    if (LiveUpdater.update(LIVE_BASE, dir, live, have, false)) {
                        append("\u062a\u0645 \u062a\u0646\u0632\u064a\u0644 \u062a\u062d\u062f\u064a\u062b \u062c\u062f\u064a\u062f \u2705\n");
                    }
                }
                entry = LiveUpdater.readEntry(live, ENTRY);
            }
            dir.mkdirs();
            Runner.run(ctx, new Console(), dir, entry);
        } catch (Throwable e) {
            append("\n" + e + "\n");
        }
        synchronized (Host.class) {
            finished = true;
        }
        append("\n[\u0627\u0646\u062a\u0647\u0649 \u0627\u0644\u0628\u0631\u0646\u0627\u0645\u062c]\n");
    }

    private static void copyAssets(AssetManager am, String assetPath, File target) throws Exception {
        String[] names = am.list(assetPath);
        if (names != null && names.length > 0) {
            target.mkdirs();
            for (String n : names) {
                copyAssets(am, assetPath + "/" + n, new File(target, n));
            }
        } else {
            File parent = target.getParentFile();
            if (parent != null) {
                parent.mkdirs();
            }
            InputStream in = am.open(assetPath);
            OutputStream out = new FileOutputStream(target);
            byte[] buf = new byte[8192];
            int r;
            while ((r = in.read(buf)) != -1) {
                out.write(buf, 0, r);
            }
            out.close();
            in.close();
        }
    }
}
