package com.plantdoctor;

import android.os.Bundle;
import android.view.WindowManager;

/**
 * Kivy activity with Android's View/HWUI renderer disabled.
 *
 * Kivy draws through SDL/OpenGL, so the Android View renderer is unnecessary.
 * Disabling it before PythonActivity creates its views avoids the ColorOS 16
 * splash/surface race seen as a crash in the hwuiTask thread.
 */
public class PlantDoctorActivity extends org.kivy.android.PythonActivity {
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED);
        super.onCreate(savedInstanceState);
    }
}
