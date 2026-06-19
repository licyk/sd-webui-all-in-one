@{
    IncludeRules = @(
        'PSReservedParams',
        'PSAvoidUsingUsernameAndPasswordParams',
        'PSAvoidUsingComputerNameHardcoded',
        'PSAvoidUsingConvertToSecureStringWithPlainText',
        'PSUseCompatibleSyntax',
        'PSDSCUseIdenticalMandatoryParametersForDSC',
        'PSDSCUseIdenticalParametersForDSC',
        'PSDSCStandardDSCFunctionsInResource'
    )
}
