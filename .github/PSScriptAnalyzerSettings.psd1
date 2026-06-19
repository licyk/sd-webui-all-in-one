@{
    IncludeRules = @(
        'PSAvoidDefaultValueSwitchParameter',
        'PSMisleadingBacktick',
        'PSMissingModuleManifestField',
        'PSReservedCmdletChar',
        'PSReservedParams',
        'PSShouldProcess',
        # 'PSUseApprovedVerbs',
        'PSAvoidUsingCmdletAliases',
        # 'PSUseDeclaredVarsMoreThanAssignments',
        'PSAvoidUsingUsernameAndPasswordParams',
        'PSAvoidUsingComputerNameHardcoded',
        'PSAvoidUsingConvertToSecureStringWithPlainText',
        'PSUseCompatibleSyntax',
        'PSDSCUseIdenticalMandatoryParametersForDSC',
        'PSDSCUseIdenticalParametersForDSC',
        'PSDSCStandardDSCFunctionsInResource'
    )
}
