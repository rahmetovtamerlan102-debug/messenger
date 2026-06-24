package com.example.messenger.models

import com.google.gson.annotations.SerializedName

data class User(
    val id: Int,
    val username: String,
    @SerializedName("first_name") val firstName: String? = null,
    @SerializedName("last_name") val lastName: String? = null
)
