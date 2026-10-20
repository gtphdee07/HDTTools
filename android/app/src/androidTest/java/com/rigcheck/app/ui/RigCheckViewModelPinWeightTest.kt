package com.rigcheck.app.ui

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.rigcheck.app.domain.computeBreakdown
import com.rigcheck.app.domain.model.ScaleTicket
import com.rigcheck.app.domain.model.TrailerTag
import com.rigcheck.app.domain.model.TruckTag
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

// The real view-model hands the pin weight slider's whole percentage points to the
// breakdown math as a fraction. PinWeightTest (JVM) pins the conversion function; this
// pins that RigCheckViewModel.breakdown actually goes through it, so a view-model that
// divides by something else (or not at all) fails here. The fractions are written out
// on purpose rather than computed, so the expected side does not share the divisor.
@RunWith(AndroidJUnit4::class)
class RigCheckViewModelPinWeightTest {

    private val truck = TruckTag(gvwrLb = 14000.0, frontGawrLb = 6000.0, rearGawrLb = 9500.0)
    private val trailer = TrailerTag(gvwrLb = 12500.0, gawrPerAxleLb = 6000.0)
    private val scale = ScaleTicket(
        steerAxleLb = 5620.0,
        driveAxleLb = 9040.0,
        trailerAxleLb = 11380.0,
        grossWeightLb = 26040.0,
    )

    private fun viewModel() = RigCheckViewModel(ApplicationProvider.getApplicationContext()).also {
        it.truck = truck
        it.trailer = trailer
        it.scale = scale
    }

    @Test
    fun theDefaultSliderPositionBreaksDownAtTwentyPercent() {
        assertEquals(computeBreakdown(truck, trailer, scale, 0.20), viewModel().breakdown)
    }

    @Test
    fun bothEndsOfTheSliderBreakDownAtTheirFractions() {
        val viewModel = viewModel()

        viewModel.pinWeightPct = 15
        assertEquals(computeBreakdown(truck, trailer, scale, 0.15), viewModel.breakdown)

        viewModel.pinWeightPct = 25
        assertEquals(computeBreakdown(truck, trailer, scale, 0.25), viewModel.breakdown)
    }
}
