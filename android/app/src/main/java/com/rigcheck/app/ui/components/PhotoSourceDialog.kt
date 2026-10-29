package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.sp
import com.rigcheck.app.ui.UiTags
import com.rigcheck.app.ui.theme.Ink
import com.rigcheck.app.ui.theme.RigCheckStyles

// The photo-source question every Scan starts with ("Take a new photo, or choose one you already have?"), on the
// Chooser and on the Truck screen's stand-alone Scan: Take Photo first, Choose from Gallery second. Each button
// closes the dialog before it calls its action.
@Composable
fun PhotoSourceDialog(onDismiss: () -> Unit, onTakePhoto: () -> Unit, onChooseFromGallery: () -> Unit) {
    RigCheckDialog(
        onDismissRequest = onDismiss,
        title = { Text("Scan Photo", style = RigCheckStyles.titleLg, color = Ink, modifier = Modifier.testTag(UiTags.PHOTO_DIALOG_TITLE)) },
        body = {
            Text(
                "Take a new photo, or choose one you already have?",
                style = RigCheckStyles.body.copy(lineHeight = 24.sp),
                color = Ink,
                modifier = Modifier.testTag(UiTags.PHOTO_DIALOG_BODY),
            )
        },
    ) {
        RigCheckButton(
            text = "Take Photo",
            onClick = {
                onDismiss()
                onTakePhoto()
            },
            size = RigCheckButtonSize.Dialog,
            icon = Icons.Filled.CameraAlt,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.PHOTO_DIALOG_CAMERA),
        )
        RigCheckButton(
            text = "Choose from Gallery",
            onClick = {
                onDismiss()
                onChooseFromGallery()
            },
            kind = RigCheckButtonKind.Secondary,
            size = RigCheckButtonSize.Dialog,
            modifier = Modifier.fillMaxWidth().testTag(UiTags.PHOTO_DIALOG_GALLERY),
        )
    }
}
