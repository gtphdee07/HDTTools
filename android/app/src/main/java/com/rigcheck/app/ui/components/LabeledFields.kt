package com.rigcheck.app.ui.components

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp

// Matches the mockup's filled-text-field style exactly (RigCheck Android
// Design.dc.html): 8dp top corners, no bottom radius, underline border.
private val fieldShape = androidx.compose.foundation.shape.RoundedCornerShape(
    topStart = 8.dp, topEnd = 8.dp, bottomStart = 0.dp, bottomEnd = 0.dp,
)

@Composable
fun LabeledTextField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String? = null,
) {
    Text(label, style = MaterialTheme.typography.labelLarge)
    TextField(
        value = value,
        onValueChange = onValueChange,
        placeholder = placeholder?.let { { Text(it) } },
        modifier = modifier.fillMaxWidth(),
        shape = fieldShape,
        colors = TextFieldDefaults.colors(),
    )
}

@Composable
fun LabeledNumberField(
    label: String,
    value: Double?,
    onValueChange: (Double?) -> Unit,
    modifier: Modifier = Modifier,
    optionalHint: String? = null,
) {
    Text(
        text = if (optionalHint != null) "$label — $optionalHint" else label,
        style = MaterialTheme.typography.labelLarge,
    )
    TextField(
        value = value?.let { if (it == it.toLong().toDouble()) it.toLong().toString() else it.toString() } ?: "",
        onValueChange = { raw -> onValueChange(raw.toDoubleOrNull()) },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
        modifier = modifier.fillMaxWidth(),
        shape = fieldShape,
        colors = TextFieldDefaults.colors(),
    )
}

@Composable
fun LabeledIntField(
    label: String,
    value: Int?,
    onValueChange: (Int?) -> Unit,
    modifier: Modifier = Modifier,
    optionalHint: String? = null,
) {
    Text(
        text = if (optionalHint != null) "$label — $optionalHint" else label,
        style = MaterialTheme.typography.labelLarge,
    )
    TextField(
        value = value?.toString() ?: "",
        onValueChange = { raw -> onValueChange(raw.toIntOrNull()) },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
        modifier = modifier.fillMaxWidth(),
        shape = fieldShape,
        colors = TextFieldDefaults.colors(),
    )
}
