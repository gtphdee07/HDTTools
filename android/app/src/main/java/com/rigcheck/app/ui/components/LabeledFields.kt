package com.rigcheck.app.ui.components

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

// The entry screens' fields, in the one field style (RigCheckTextField). `modifier` goes on the input itself (the
// tag, so a test can type into it and the map's 56 dp box is what is measured); the label is above it, with "— optional"
// after it for an optional one; `unit` is the hint at the right of the box ("lb"); `help` is the line under it.

@Composable
fun LabeledTextField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String? = null,
    labelBadge: (@Composable () -> Unit)? = null,
) {
    RigCheckTextField(
        label = label,
        value = value,
        onValueChange = onValueChange,
        inputModifier = modifier,
        placeholder = placeholder,
        labelBadge = labelBadge,
    )
}

@Composable
fun LabeledNumberField(
    // null: no label above the box, for a field a text of its own already labels (the stand-alone weight).
    label: String?,
    value: Double?,
    onValueChange: (Double?) -> Unit,
    modifier: Modifier = Modifier,
    optionalHint: String? = null,
    unit: String? = null,
    help: String? = null,
    helpModifier: Modifier = Modifier,
    labelBadge: (@Composable () -> Unit)? = null,
) {
    RigCheckTextField(
        label = if (label != null && optionalHint != null) "$label — $optionalHint" else label,
        value = value?.let { if (it == it.toLong().toDouble()) it.toLong().toString() else it.toString() } ?: "",
        onValueChange = { raw -> onValueChange(raw.toDoubleOrNull()) },
        inputModifier = modifier,
        numeric = true,
        unit = unit,
        help = help,
        helpModifier = helpModifier,
        labelBadge = labelBadge,
    )
}

@Composable
fun LabeledIntField(
    label: String,
    value: Int?,
    onValueChange: (Int?) -> Unit,
    modifier: Modifier = Modifier,
    optionalHint: String? = null,
    help: String? = null,
    helpModifier: Modifier = Modifier,
) {
    RigCheckTextField(
        label = if (optionalHint != null) "$label — $optionalHint" else label,
        value = value?.toString() ?: "",
        onValueChange = { raw -> onValueChange(raw.toIntOrNull()) },
        inputModifier = modifier,
        numeric = true,
        help = help,
        helpModifier = helpModifier,
    )
}
