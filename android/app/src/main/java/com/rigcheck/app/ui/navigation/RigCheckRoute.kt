package com.rigcheck.app.ui.navigation

import kotlinx.serialization.Serializable

enum class EntryModule { TRUCK, TRAILER, SCALE }

sealed interface RigCheckRoute {
    @Serializable
    data object RigPicker : RigCheckRoute

    @Serializable
    data class Chooser(val module: EntryModule) : RigCheckRoute

    @Serializable
    data object Paywall : RigCheckRoute

    @Serializable
    data object TruckTagEntry : RigCheckRoute

    @Serializable
    data object TrailerTagEntry : RigCheckRoute

    @Serializable
    data object ScaleTicketEntry : RigCheckRoute

    @Serializable
    data object Disclaimer : RigCheckRoute

    @Serializable
    data object Results : RigCheckRoute
}
