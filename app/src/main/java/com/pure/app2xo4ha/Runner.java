package com.pure.app2xo4ha;

import android.content.Context;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;

final class Runner {

    private static final int WEB_PORT = 8080;

    private Runner() {
    }

    static void run(Context ctx, Host.Console console, File dir, String entry) throws Throwable {
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(ctx));
        }
        File data = new File(ctx.getFilesDir(), "data");
        data.mkdirs();
        Python.getInstance().getModule("pure_runner").callAttr("run", console, dir.getAbsolutePath(), entry, WEB_PORT, data.getAbsolutePath());
    }
}
