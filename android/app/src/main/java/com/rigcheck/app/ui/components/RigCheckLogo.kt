package com.rigcheck.app.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.rigcheck.app.R
import com.rigcheck.app.ui.theme.Radii
import com.rigcheck.app.ui.theme.Sizes
import com.rigcheck.app.ui.theme.Surface as SurfaceWhite

// The app's mark: the 52 dp logo in a 14 dp rounded square with a 2 dp white border (so 56 dp in all), as the Rig
// picker's top bar and the empty states (the picker's and the History's) draw it.
@Composable
fun RigCheckLogo(modifier: Modifier = Modifier) {
    val shape = RoundedCornerShape(Radii.Card)
    Image(
        painter = painterResource(R.drawable.logo),
        contentDescription = null,
        contentScale = ContentScale.Crop,
        modifier = modifier
            .size(Sizes.TopBarLogo + 4.dp)
            .border(2.dp, SurfaceWhite, shape)
            .padding(2.dp)
            .clip(shape),
    )
}
