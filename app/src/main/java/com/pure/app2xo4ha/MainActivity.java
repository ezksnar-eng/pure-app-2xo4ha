package com.pure.app2xo4ha;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.net.InetSocketAddress;
import java.net.Socket;

public class MainActivity extends Activity implements Host.Listener {

    private static final String STATUS_COLOR = "#c81466";
    private static final int WEB_PORT = 8080;
    private static final boolean BG = false;

    private FrameLayout frame;
    private LinearLayout consoleView;
    private ScrollView scroll;
    private TextView output;
    private EditText input;
    private WebView webView;
    private Button toggle;
    private boolean showingWeb = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        try {
            getWindow().setStatusBarColor(Color.parseColor(STATUS_COLOR));
        } catch (Exception ignored) {
        }
        buildUi();
        if (BG) {
            if (Build.VERSION.SDK_INT >= 33) {
                requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, 7);
            }
            Intent svc = new Intent(this, HostService.class);
            if (Build.VERSION.SDK_INT >= 26) {
                startForegroundService(svc);
            } else {
                startService(svc);
            }
        }
        Host.start(this);
        Host.attach(this);
        if (WEB_PORT > 0) {
            watchPort();
        }
    }

    private int dp(int v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private void buildUi() {
        frame = new FrameLayout(this);
        frame.setBackgroundColor(0xFF1A0510);

        consoleView = new LinearLayout(this);
        consoleView.setOrientation(LinearLayout.VERTICAL);

        scroll = new ScrollView(this);
        output = new TextView(this);
        output.setTextColor(0xFFFFD6EA);
        output.setTypeface(Typeface.MONOSPACE);
        output.setTextSize(13f);
        output.setPadding(dp(12), dp(12), dp(12), dp(12));
        output.setTextIsSelectable(true);
        scroll.addView(output, new ScrollView.LayoutParams(ScrollView.LayoutParams.MATCH_PARENT, ScrollView.LayoutParams.WRAP_CONTENT));
        consoleView.addView(scroll, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setBackgroundColor(0xFF2A0A1C);
        bar.setPadding(dp(8), dp(6), dp(8), dp(6));

        input = new EditText(this);
        input.setSingleLine(true);
        input.setTextColor(Color.WHITE);
        input.setHintTextColor(0xFF9D6B86);
        input.setHint(">");
        input.setImeOptions(EditorInfo.IME_ACTION_SEND);
        input.setOnEditorActionListener(new TextView.OnEditorActionListener() {
            @Override
            public boolean onEditorAction(TextView v, int actionId, KeyEvent event) {
                submit();
                return true;
            }
        });
        bar.addView(input, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));

        Button send = new Button(this);
        send.setText("\u0625\u0631\u0633\u0627\u0644");
        send.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                submit();
            }
        });
        bar.addView(send, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        if (BG) {
            Button stop = new Button(this);
            stop.setText("\u0625\u064a\u0642\u0627\u0641");
            stop.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    stopService(new Intent(MainActivity.this, HostService.class));
                    finishAffinity();
                    android.os.Process.killProcess(android.os.Process.myPid());
                }
            });
            bar.addView(stop, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        }

        consoleView.addView(bar, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));
        frame.addView(consoleView, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        toggle = new Button(this);
        toggle.setText("\u0627\u0644\u0633\u062c\u0644");
        toggle.setVisibility(View.GONE);
        toggle.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                toggleView();
            }
        });
        frame.addView(toggle, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.TOP | Gravity.END));

        setContentView(frame);
    }

    private void submit() {
        String t = input.getText().toString();
        input.setText("");
        output.append(t + "\n");
        Host.submit(t);
    }

    @Override
    public void onAppend(final String text) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                output.append(text);
                scroll.post(new Runnable() {
                    @Override
                    public void run() {
                        scroll.fullScroll(View.FOCUS_DOWN);
                    }
                });
            }
        });
    }

    private void watchPort() {
        Thread t = new Thread(new Runnable() {
            @Override
            public void run() {
                long t0 = System.currentTimeMillis();
                while (System.currentTimeMillis() - t0 < 180000L) {
                    if (portOpen(WEB_PORT)) {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                showWeb();
                            }
                        });
                        return;
                    }
                    try {
                        Thread.sleep(500);
                    } catch (InterruptedException e) {
                        return;
                    }
                }
            }
        });
        t.setDaemon(true);
        t.start();
    }

    private boolean portOpen(int port) {
        Socket s = new Socket();
        try {
            s.connect(new InetSocketAddress("127.0.0.1", port), 300);
            return true;
        } catch (Exception e) {
            return false;
        } finally {
            try {
                s.close();
            } catch (Exception ignored) {
            }
        }
    }

    private void showWeb() {
        if (showingWeb) {
            return;
        }
        showingWeb = true;
        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        webView.setWebViewClient(new WebViewClient());
        frame.addView(webView, 0, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        consoleView.setVisibility(View.GONE);
        toggle.setVisibility(View.VISIBLE);
        webView.loadUrl("http://127.0.0.1:" + WEB_PORT + "/");
    }

    private void toggleView() {
        if (webView == null) {
            return;
        }
        boolean webVisible = webView.getVisibility() == View.VISIBLE;
        webView.setVisibility(webVisible ? View.GONE : View.VISIBLE);
        consoleView.setVisibility(webVisible ? View.VISIBLE : View.GONE);
    }

    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() {
        if (showingWeb && webView != null && webView.getVisibility() == View.VISIBLE && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        Host.attach(null);
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
